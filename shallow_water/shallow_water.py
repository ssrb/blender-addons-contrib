#
# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****
'''
    "name": "Shallow Water Body Importer",
    "author": "Sebastien S. R. Bigot (ssrb)"
    "version": (0, 0, 1),
'''

import bpy
from math import *
from bpy.props import *
from os.path import splitext, isfile

def create_mesh_object(context, verts, edges, faces, name):
    mesh = bpy.data.meshes.new(name) 
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    from bpy_extras import object_utils
    return object_utils.object_data_add(context, mesh, operator=None)

def goto_section(mfile, section):
    for line in mfile:
        if line.rstrip() == section:
            return
    raise Exception("Cannot find section " + section)

def parse_vertices(mfile):
    goto_section(mfile, "Vertices")
    nbVertices = int(mfile.readline())
    vertices = []
    for i in range(nbVertices):
        desc = mfile.readline().split()
        vertices.append([float(desc[0]), float(desc[1]), 0.])
    return vertices

def parse_triangles(mfile):
    goto_section(mfile, "Triangles")
    nbTriangles = int(mfile.readline())
    triangles = []
    for i in range(nbTriangles):
        desc = mfile.readline().split()
        triangles.append([int(desc[0]) - 1, int(desc[1]) - 1, int(desc[2]) - 1])
    return triangles

def renumber_boundary(edges, vertices):
    vis = sorted(set([vi for edge in edges for vi in edge]))
    global2local = dict()
    local = 0
    for vi in vis:
       global2local[vi] = local
       local += 1
    return [[global2local[edge[0]], global2local[edge[1]]] for edge in edges], \
        [vertices[vi] for vi in sorted(global2local.keys())], vis

def parse_boundaries(mfile, vertices):
    goto_section(mfile, "Edges")
    nbEdges = int(mfile.readline())
    oedges = []
    cedges = []
    for _ in range(nbEdges):
        desc = mfile.readline().split()
        (oedges if int(desc[2]) == 2 else cedges).append([int(desc[0]) - 1, int(desc[1]) - 1])
    oedges, overtices, rawovertices = renumber_boundary(oedges, vertices)
    cedges, cvertices, rawoedges = renumber_boundary(cedges, vertices)    
    return oedges, overtices, cedges, cvertices, rawovertices, rawoedges

def parse_mesh_file(meshfilepath):
    mfile = open(meshfilepath)
    allvertices = parse_vertices(mfile)
    oedges, overtices, cedges, cvertices, rawovertices, rawoedges = parse_boundaries(mfile, allvertices)
    triangles = parse_triangles(mfile)
    return oedges, overtices, cedges, cvertices, rawovertices, rawoedges, allvertices, triangles

def parse_depth_file(depthfilepath):
    dfile = open(depthfilepath)
    depths = []
    for line in dfile:
        depths.append(float(line))
    return depths

def CreateRevCxnTable(triangles):
    rct = dict()
    for tid, triangle in enumerate(triangles):
        for vid in triangle:
            if vid in rct:
                rct[vid].add(tid)
            else:
                rct[vid] = set([tid])
    return rct

def rotate(l):
    if len(l) == 0:
        return []
    for e in l[1:]:
        yield e
    yield l[0]

def need_wall(j1, j2, depth, alldepths, rct):
    return (j2[0] - j1[0]) % 3 == 1 and any(alldepths[tid] != depth for tid in rct[j1[1]] & rct[j2[1]])

def climb(moving, target, jumps, allvertices):
    z = 2
    while allvertices[moving][z] < allvertices[target][z] and moving in jumps:
        moving = jumps[moving]
    return moving

def build_single_wall(lvid, rvid, jumps, allvertices):
    wall = []

    lvid = climb(lvid, rvid, jumps, allvertices)
    rvid = climb(rvid, lvid, jumps, allvertices)

    while lvid in jumps or rvid in jumps:
        if lvid in jumps:
            wall.append([lvid, rvid, jumps[lvid]])
            lvid = jumps[lvid]
        if rvid in jumps:
            wall.append([rvid, jumps[rvid], lvid])
            rvid = jumps[rvid]
    return wall

def build_walls(depth, alldepths, ljump, jumps, rct, allvertices):
    z = 2
    walls = []
    for j1, j2 in zip(ljump, rotate(ljump)):
        if need_wall(j1, j2, depth, alldepths, rct):    
            walls += build_single_wall(j1[1], j2[1], jumps, allvertices)
    return walls

def jump(sid, vid, depth, jumps, triangle, allvertices):
    z = 2
    while vid in jumps:
        vid = jumps[vid]
    vertex = allvertices[vid]
    if vertex[z] == depth:
        triangle[sid] = vid
    else:
        newvertex = list(vertex)
        newvertex[z] = depth
        jumps[vid] = triangle[sid] = len(allvertices)
        allvertices.append(newvertex)

def build_bottom(depthfilepath, triangles, allvertices):

    z = 2

    depths = parse_depth_file(depthfilepath)
    
    perm = sorted(range(len(triangles)), key = lambda k : depths[k])
    triangles = [triangles[p] for p in perm]
    alldepths = [depths[p] for p in perm]

    jumps = dict()
    walls = []

    rct = CreateRevCxnTable(triangles)

    for tid, triangle in enumerate(triangles):
        depth = alldepths[tid]
        ljump = []
        for sid, vid in enumerate(triangle):
            vertex = allvertices[vid]
            if vertex[z] == 0:
                vertex[z] = depth
            elif vertex[z] != depth:
                ljump.append([sid, vid])
                jump(sid, vid, depth, jumps, triangle, allvertices)
                                                   
        walls += build_walls(depth, alldepths, ljump, jumps, rct, allvertices)

    return triangles + walls

def load(self, context, filepath, import_bottom=False, separate_boundary_objects=True):

    if len(filepath):
        
        basename, _ = splitext(filepath)

        oedges, overtices, cedges, cvertices, rawovertices, rawoedges, allvertices, alltriangles = parse_mesh_file(filepath)
        
        water = create_mesh_object(context, allvertices, [], alltriangles, "ShallowWaterBody")
        closedgrp = water.object.vertex_groups.new("ClosedBoundary")
        closedgrp.add(rawoedges, 1.0, 'REPLACE')
        opengrp = water.object.vertex_groups.new("OpenBoundary")
        opengrp.add(rawovertices, 1.0, 'REPLACE')

        if separate_boundary_objects:
            create_mesh_object(context, cvertices, cedges, [], "ClosedBoundary")
            create_mesh_object(context, overtices, oedges, [], "OpenBoundary")

        depthfile = basename + ".depth"        
        if import_bottom and isfile(depthfile):
            bottom = build_bottom(depthfile, alltriangles, allvertices)
            bottom = create_mesh_object(context, allvertices, [], bottom, "Bottom")
            closedgrp = bottom.object.vertex_groups.new("ClosedBoundary")
            closedgrp.add(rawoedges, 1.0, 'REPLACE')
            opengrp = bottom.object.vertex_groups.new("OpenBoundary")
            opengrp.add(rawovertices, 1.0, 'REPLACE')
            bottom.object.scale = (1, 1, -0.01)

        solutionfile = basename + ".solution"        
        if isfile(solutionfile):
            modifier = water.object.modifiers.new("sw", type='SHALLOW_WATER')
            modifier.solution = solutionfile

    return {'FINISHED'}
