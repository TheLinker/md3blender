#"""
#Name: 'MD3 (.md3)'
#bpy: 243
#Group: 'Import'
#Tooltip: 'Import from Quake3 file format. (.md3)'
#"""

bl_info = {
	"name": "MD3 Importer",
	"description": "MD3 Importer",
	"author": "PhaethonH, Bob Holcomb, Robert (Tr3B) Beckebans, f0rqu3, TheLinker",
	"version": (0, 8, 0),
	"blender": (2, 5, 9),
	"api": 31847,
	"location": "File > Import",
	"warning": "", # used for warning icon and text in addons panel
	"wiki_url": ""
#	"wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/"\
#        "Scripts/File_I-O/idTech3_md3",
	"tracker_url": "https://github.com/TheLinker/md3blender",
	"category": "Import/Export"}

from md3_utils.md3 import *
from md3_utils.md3_shared import *

import bpy, os
import mathutils

log = Logger("md3_import_log")

def Import(fileName):
	#log starts here
	log.info("Starting ...")

	log.info("Importing MD3 model: %s", fileName)

	pathName = StripGamePath(StripModel(fileName))
	log.info("Shader path name: %s", pathName)

	modelName = StripExtension(StripPath(fileName))
	log.info("Model name: %s", modelName)

	# read the file in
	file = open(fileName,"rb")
	md3 = md3Object()
	if md3.Load(file, log) == None :
		return
	md3.Dump(log)
	file.close()

	scene = bpy.context.scene

	for k in range(md3.numSurfaces):

		surface = md3.surfaces[k]

		# create a new mesh
		mesh = bpy.data.meshes.new(surface.name)

		# create the verts
		mesh.vertices.add(surface.numVerts)
		for i in range(surface.numVerts) :
			mesh.vertices[i].co = surface.verts[i].xyz

		#set vertex normal and uv
		for i in range(len(mesh.vertices)):
			mesh.vertices[i].normal=mathutils.Vector( surface.verts[i].normal )
#			mesh.vertices[i].uvco=mathutils.Vector(surface.uv[i].u, surface.uv[i].v)

		# create the faces
		mesh.faces.add(surface.numTriangles)
		for i in range(surface.numTriangles) :
			mesh.faces[i].vertices = surface.triangles[i].indexes

#		# vertex uv to face uv
#		mesh.faceUV=True
#		for f in mesh.faces:
#			f.uv = [v.uvco for v in f.verts]
#			f.smooth=1

		# create materials for surface
		for i in range(surface.numShaders):

			# create new material if necessary
			matName = StripExtension(StripPath(surface.shaders[i].name))
			log.info("Material %s shader: %s", matName, surface.shaders[i].name)
			if matName == "" :
				matName = surface.name + "_mat"

			mat = bpy.data.materials.get(matName, None)

			if mat == None :
				log.info("Creating new material: %s", matName)
				mat = bpy.data.materials.new(matName)
				# create new texture
				texture = mesh.uv_textures.new(matName)
				# try .tga by default
				#imageName = GAMEDIR + surface.shaders[i].name + '.tga'
				imageName = pathName+matName+'.tga'
				try:
					image = bpy.data.images.load(imageName)
				except (IOError, RuntimeError) :
					try:
						imageName = pathName+matName+'.png'
						image = bpy.data.images.load(imageName)
					except (IOError, RuntimeError) :
						try:
							imageName = pathName+matName+'.jpg'
							image = bpy.data.images.load(imageName)
						except (IOError, RuntimeError) :
							log.warning("Unable to load image for %s", imageName)

				for i, f in enumerate(texture.data) :
					f.image = image
					f.use_image = True
					tri = surface.triangles[i]
					f.uv1 = mathutils.Vector((surface.uv[tri.indexes[0]].u, surface.uv[tri.indexes[0]].v))
					f.uv2 = mathutils.Vector((surface.uv[tri.indexes[1]].u, surface.uv[tri.indexes[1]].v))
					f.uv3 = mathutils.Vector((surface.uv[tri.indexes[2]].u, surface.uv[tri.indexes[2]].v))

				# texture to material
				tex_slot = mat.texture_slots.add()
				tex_slot.texture_coords = 'UV'
				tex_slot.uv_layer = matName

			# append material to the mesh's list of materials
			mesh.materials.append(mat)
			#mesh.update()

		# add object
		meshObject= bpy.data.objects.new(surface.name, mesh)
#		meshObject.link(mesh)
		scene.objects.link(meshObject)

################
		if surface.numFrames > 1 :
			# animate the verts through keyframe animation
			for i in range(surface.numFrames):

				# update the vertices
				for j in range(surface.numVerts):
					xyz=bpy.Mathutils.Vector(surface.verts[(i * surface.numVerts) + j].xyz)
					normal=bpy.Mathutils.Vector(surface.verts[(i * surface.numVerts) + j].normal)
					mesh.verts[j].no = normal
					mesh.verts[j].co = xyz

				meshObject.insertShapeKey()

			meshKey = mesh.key
			meshKey.ipo = bpy.Ipo.New('Key', surface.name + "_ipo")

			index = 1
			for curveName in meshKey.ipo.curveConsts :
				#print curveName
				meshKey.ipo.addCurve(curveName)
				meshKey.ipo[curveName].interpolation=bpy.IpoCurve.InterpTypes.CONST
				meshKey.ipo[curveName].addBezier((0,0))
				meshKey.ipo[curveName].addBezier((index,1))
				meshKey.ipo[curveName].addBezier((index+1,0))
				index+=1
###############################

	# select all and remove doubles
		#mesh.sel=1
		#mesh.remDoubles(0.0)

	# create tags
	for i in range(md3.numTags):
		tag = md3.tags[i]
		# this should be an Empty object
		blenderTag = bpy.data.objects.new(tag.name, None);
		scene.objects.link(blenderTag)
		blenderTag.location = tag.origin

		if md3.numFrames > 1 :
			# set ipo
			ipo = bpy.Ipo.New('Object', tag.name + "_ipo")
			locX = ipo.addCurve('LocX')
			locY = ipo.addCurve('LocY')
			locZ = ipo.addCurve('LocZ')
			rotX = ipo.addCurve('RotX')
			rotY = ipo.addCurve('RotY')
			rotZ = ipo.addCurve('RotZ')
			locX.interpolation=bpy.IpoCurve.InterpTypes.CONST
			locY.interpolation=bpy.IpoCurve.InterpTypes.CONST
			locZ.interpolation=bpy.IpoCurve.InterpTypes.CONST
			rotX.interpolation=bpy.IpoCurve.InterpTypes.CONST
			rotY.interpolation=bpy.IpoCurve.InterpTypes.CONST
			rotZ.interpolation=bpy.IpoCurve.InterpTypes.CONST
			#set ipo for tag
			blenderTag.setIpo(ipo)

			for j in range(md3.numFrames):
				tag = md3.tags[j * md3.numTags + i]

				# Note: Quake3 uses left-hand geometry
				forward = [tag.axis[0], tag.axis[1], tag.axis[2]]
				left = [tag.axis[3], tag.axis[4], tag.axis[5]]
				up = [tag.axis[6], tag.axis[7], tag.axis[8]]

				rotation = bpy.Mathutils.Matrix(forward, left, up)
				rot_Euler=rotation.toEuler()

				locX.addBezier((j+1,tag.origin[0]))
				locY.addBezier((j+1,tag.origin[1]))
				locZ.addBezier((j+1,tag.origin[2]))
				#blender: 100 degrees -> 10 units in IPO -> BLARGH
				rotX.addBezier((j+1,rot_Euler.x/10))
				rotY.addBezier((j+1,rot_Euler.y/10))
				rotZ.addBezier((j+1,rot_Euler.z/10))

##########
#import class registration and interface
from bpy.props import *
class ImportMD3(bpy.types.Operator):
	'''Export to Quake Model 5 (.md5)'''
	bl_idname = "import.md3"
	bl_label = 'Import MD3'

	logenum = [("console","Console","log to console"),
			 ("append","Append","append to log file"),
			 ("overwrite","Overwrite","overwrite log file")]

  #search for list of actions to import
	filepath = StringProperty(subtype = 'FILE_PATH',name="File Path", description="Filepath for importing", maxlen= 1024, default= "")

	def execute(self, context):
		Import(self.filepath)
		return {'FINISHED'}

	def invoke(self, context, event):
		WindowManager = context.window_manager
		# fixed for 2.56? Katsbits.com (via Nic B)
		# original WindowManager.add_fileselect(self)
		WindowManager.fileselect_add(self)
		return {"RUNNING_MODAL"}

def menu_func(self, context):
	default_path = os.path.splitext(bpy.data.filepath)[0]
	self.layout.operator(ImportMD3.bl_idname, text="Quake Model 3 (.md3)", icon='BLENDER').filepath = default_path

def register():
	bpy.utils.register_module(__name__)  #mikshaw
	bpy.types.INFO_MT_file_import.append(menu_func)

def unregister():
	bpy.utils.unregister_module(__name__)  #mikshaw
	bpy.types.INFO_MT_file_import.remove(menu_func)

if __name__ == "__main__":
	register()
