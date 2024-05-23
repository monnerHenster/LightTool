# SPDX-FileCopyrightText: 2019-2022 Blender Foundation
#
# SPDX-License-Identifier: GPL-2.0-or-later

# author Daniel Schalla, maintained by meta-androcto

bl_info = {
    "name": "Tri-lighting Procedure",
    "author": "Daniel Schalla , Monkeyxox",
    "version": (0, 1, 5),
    "blender": (4, 00, 0),
    "location": "View3D > Add > Lights",
    "description": "Add 3 Point Lighting to Selected / Active Object and keep procedure panel",
    "warning": "",
    "tracker_url": "https://developer.blender.org/maniphest/task/edit/form/2/",
    "doc_url": "{BLENDER_MANUAL_URL}/addons/lighting/trilighting.html",
    "category": "Lighting",
}

import bpy
from bpy.types import Operator
from bpy.props import (
        EnumProperty,
        FloatProperty,
        IntProperty,
        StringProperty,
        )
from math import (
        sin, cos,
        radians,
        sqrt,
        )

DEFAULT_LIGHT = ['key','back','fill']

class LT_OP_Panel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Common"
    bl_category = "LightTool"
    bl_idname = "LT_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        ppts = bpy.context.scene.LightToolAttr
        layout = self.layout

        # light_tool.trilighting
        row = layout.row()
        row.operator('light_tool.trilighting')

        layout.label(text="Position:")
        col = layout.column(align=True)
        col.prop(ppts, "height")
        col.prop(ppts, "distance")

        layout.label(text="Light:")
        col = layout.column(align=True)
        col.prop(ppts, "energy")
        col.prop(ppts, "contrast")

        layout.label(text="Orientation:")
        col = layout.column(align=True)
        col.prop(ppts, "leftangle")
        col.prop(ppts, "rightangle")
        col.prop(ppts, "backangle")

        col = layout.column()
        col.label(text="Key Light Type:")
        col.prop(ppts, "primarytype", text="")
        col.label(text="Fill + Back Type:")
        col.prop(ppts, "secondarytype", text="")

def get_light_data(name:str, type:any):
    backData = bpy.data.lights.get(name)
    if backData:
        backData = bpy.data.lights[name]
    else:
        backData = bpy.data.lights.new(name=name, type=type)
    return backData

class LT_OT_TriLighting(Operator):
    bl_idname = "light_tool.trilighting"
    bl_label = "Tri-Lighting Creator"
    bl_description = ("Add 3 Point Lighting to Selected / Active Object\n"
                      "Needs an existing Active Object")
    bl_options = {'REGISTER', 'UNDO'}
    COMPAT_ENGINES = {'CYCLES', 'EEVEE'}


    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ppts = bpy.context.scene.LightToolAttr

        try:
            collection = context.collection
            scene = context.scene
            view = context.space_data
            if view.type == 'VIEW_3D':
                camera = view.camera
            else:
                camera = scene.camera

            if (camera is None):
                cam_data = bpy.data.cameras.new(name='Camera')
                cam_obj = bpy.data.objects.new(name='Camera', object_data=cam_data)
                collection.objects.link(cam_obj)
                scene.camera = cam_obj
                bpy.ops.view3d.camera_to_view()
                camera = cam_obj
                # Leave camera view again, otherwise redo does not work correctly.
                bpy.ops.view3d.view_camera()

            obj = bpy.context.view_layer.objects.active

            # Calculate Energy for each Lamp
            if(ppts.contrast > 0):
                keyEnergy = ppts.energy
                backEnergy = (ppts.energy / 100) * abs(ppts.contrast)
                fillEnergy = (ppts.energy / 100) * abs(ppts.contrast)
            else:
                keyEnergy = (ppts.energy / 100) * abs(ppts.contrast)
                backEnergy = ppts.energy
                fillEnergy = ppts.energy

            # Calculate Direction for each Lamp

            # Calculate current Distance and get Delta
            obj_position = obj.location
            cam_position = camera.location

            delta_position = cam_position - obj_position
            vector_length = sqrt(
                            (pow(delta_position.x, 2) +
                             pow(delta_position.y, 2) +
                             pow(delta_position.z, 2))
                            )
            if not vector_length:
                # division by zero most likely
                self.report({'WARNING'},
                            "Operation Cancelled. No viable object in the scene")

                return {'CANCELLED'}

            single_vector = (1 / vector_length) * delta_position

            # Calc back position
            singleback_vector = single_vector.copy()
            singleback_vector.x = cos(radians(ppts.backangle)) * single_vector.x + \
                                  (-sin(radians(ppts.backangle)) * single_vector.y)

            singleback_vector.y = sin(radians(ppts.backangle)) * single_vector.x + \
                                 (cos(radians(ppts.backangle)) * single_vector.y)

            backx = obj_position.x + ppts.distance * singleback_vector.x
            backy = obj_position.y + ppts.distance * singleback_vector.y

            backData = get_light_data(name="TriLamp-Back", type=ppts.secondarytype)
            backData.energy = backEnergy

            backLamp = bpy.data.objects.new(name="TriLamp-Back", object_data=backData)
            collection.objects.link(backLamp)
            backLamp.location = (backx, backy, ppts.height)

            trackToBack = backLamp.constraints.new(type="TRACK_TO")
            trackToBack.target = obj
            trackToBack.track_axis = "TRACK_NEGATIVE_Z"
            trackToBack.up_axis = "UP_Y"

            # Calc right position
            singleright_vector = single_vector.copy()
            singleright_vector.x = cos(radians(ppts.rightangle)) * single_vector.x + \
                                  (-sin(radians(ppts.rightangle)) * single_vector.y)

            singleright_vector.y = sin(radians(ppts.rightangle)) * single_vector.x + \
                                  (cos(radians(ppts.rightangle)) * single_vector.y)

            rightx = obj_position.x + ppts.distance * singleright_vector.x
            righty = obj_position.y + ppts.distance * singleright_vector.y

            rightData = bpy.data.lights.new(name="TriLamp-Fill", type=ppts.secondarytype)
            rightData.energy = fillEnergy
            rightLamp = bpy.data.objects.new(name="TriLamp-Fill", object_data=rightData)
            collection.objects.link(rightLamp)
            rightLamp.location = (rightx, righty, ppts.height)
            trackToRight = rightLamp.constraints.new(type="TRACK_TO")
            trackToRight.target = obj
            trackToRight.track_axis = "TRACK_NEGATIVE_Z"
            trackToRight.up_axis = "UP_Y"

            # Calc left position
            singleleft_vector = single_vector.copy()
            singleleft_vector.x = cos(radians(-ppts.leftangle)) * single_vector.x + \
                                (-sin(radians(-ppts.leftangle)) * single_vector.y)
            singleleft_vector.y = sin(radians(-ppts.leftangle)) * single_vector.x + \
                                (cos(radians(-ppts.leftangle)) * single_vector.y)
            leftx = obj_position.x + ppts.distance * singleleft_vector.x
            lefty = obj_position.y + ppts.distance * singleleft_vector.y

            leftData = bpy.data.lights.new(name="TriLamp-Key", type=ppts.primarytype)
            leftData.energy = keyEnergy

            leftLamp = bpy.data.objects.new(name="TriLamp-Key", object_data=leftData)
            collection.objects.link(leftLamp)
            leftLamp.location = (leftx, lefty, ppts.height)
            trackToLeft = leftLamp.constraints.new(type="TRACK_TO")
            trackToLeft.target = obj
            trackToLeft.track_axis = "TRACK_NEGATIVE_Z"
            trackToLeft.up_axis = "UP_Y"

        except Exception as e:
            self.report({'WARNING'},
                        "Some operations could not be performed (See Console for more info)")

            print("\n[Add Advanced  Objects]\nOperator: "
                  "object.trilighting\nError: {}".format(e))

            return {'CANCELLED'}

        return {'FINISHED'}
    
def menu_func(self, context):
    self.layout.operator(LT_OT_TriLighting.bl_idname, text="3 Point Lights", icon='LIGHT')

def update_energy(self,context):
    ppts = bpy.context.scene.LightToolAttr

    if(ppts.contrast > 0):
        get_light_data(name='TriLamp-Key',type=ppts.primarytype).energy = ppts.energy
        get_light_data(name='TriLamp-Back',type=ppts.primarytype).energy = (ppts.energy / 100) * abs(ppts.contrast)
        get_light_data(name='TriLamp-Fill',type=ppts.primarytype).energy = (ppts.energy / 100) * abs(ppts.contrast)
    else:
        get_light_data(name='TriLamp-Key',type=ppts.primarytype).energy = (ppts.energy / 100) * abs(ppts.contrast)
        get_light_data(name='TriLamp-Back',type=ppts.primarytype).energyy = ppts.energy
        get_light_data(name='TriLamp-Fill',type=ppts.primarytype).energyy = ppts.energy

def update_back_angle(self,context):
    obj = bpy.context.view_layer.objects.active
    camera = bpy.data.objects.get('Camera')
    obj_position = obj.location
    cam_position = camera.location

    delta_position = cam_position - obj_position
    vector_length = sqrt(
                    (pow(delta_position.x, 2) +
                        pow(delta_position.y, 2) +
                        pow(delta_position.z, 2))
                    )
    if not vector_length:
        # division by zero most likely
        self.report({'WARNING'},
                    "Operation Cancelled. No viable object in the scene")

        return {'CANCELLED'}

    single_vector = (1 / vector_length) * delta_position

    # Calc back position
    ppts = bpy.context.scene.LightToolAttr
    singleback_vector = single_vector.copy()
    singleback_vector.x = cos(radians(ppts.backangle)) * single_vector.x + \
                            (-sin(radians(ppts.backangle)) * single_vector.y)

    singleback_vector.y = sin(radians(ppts.backangle)) * single_vector.x + \
                            (cos(radians(ppts.backangle)) * single_vector.y)

    backx = obj_position.x + ppts.distance * singleback_vector.x
    backy = obj_position.y + ppts.distance * singleback_vector.y

    backLamp = bpy.data.objects.get("TriLamp-Back")
    backLamp.location = (backx, backy, ppts.height)

def update_left_angle(self,context):
    obj = bpy.context.view_layer.objects.active
    camera = bpy.data.objects.get('Camera')
    obj_position = obj.location
    cam_position = camera.location

    delta_position = cam_position - obj_position
    vector_length = sqrt(
                    (pow(delta_position.x, 2) +
                        pow(delta_position.y, 2) +
                        pow(delta_position.z, 2))
                    )
    if not vector_length:
        # division by zero most likely
        self.report({'WARNING'},
                    "Operation Cancelled. No viable object in the scene")

        return {'CANCELLED'}

    single_vector = (1 / vector_length) * delta_position

    # Calc back position
    ppts = bpy.context.scene.LightToolAttr
    singleback_vector = single_vector.copy()
    singleback_vector.x = cos(radians(-ppts.leftangle)) * single_vector.x + \
                            (-sin(radians(-ppts.leftangle)) * single_vector.y)

    singleback_vector.y = sin(radians(-ppts.leftangle)) * single_vector.x + \
                            (cos(radians(-ppts.leftangle)) * single_vector.y)
    
    # singleleft_vector.x = cos(radians(-ppts.leftangle)) * single_vector.x + \
    #                     (-sin(radians(-ppts.leftangle)) * single_vector.y)
    # singleleft_vector.y = sin(radians(-ppts.leftangle)) * single_vector.x + \
    #                     (cos(radians(-ppts.leftangle)) * single_vector.y)
    # leftx = obj_position.x + ppts.distance * singleleft_vector.x
    # lefty = obj_position.y + ppts.distance * singleleft_vector.y

    backx = obj_position.x + ppts.distance * singleback_vector.x
    backy = obj_position.y + ppts.distance * singleback_vector.y

    backLamp = bpy.data.objects.get("TriLamp-Key")
    backLamp.location = (backx, backy, ppts.height)

def update_right_angle(self,context):
    obj = bpy.context.view_layer.objects.active
    camera = bpy.data.objects.get('Camera')
    obj_position = obj.location
    cam_position = camera.location

    delta_position = cam_position - obj_position
    vector_length = sqrt(
                    (pow(delta_position.x, 2) +
                        pow(delta_position.y, 2) +
                        pow(delta_position.z, 2))
                    )
    if not vector_length:
        # division by zero most likely
        self.report({'WARNING'},
                    "Operation Cancelled. No viable object in the scene")

        return {'CANCELLED'}

    single_vector = (1 / vector_length) * delta_position

    # Calc back position
    ppts = bpy.context.scene.LightToolAttr
    singleback_vector = single_vector.copy()
    singleback_vector.x = cos(radians(ppts.rightangle)) * single_vector.x + \
                            (-sin(radians(ppts.rightangle)) * single_vector.y)

    singleback_vector.y = sin(radians(ppts.rightangle)) * single_vector.x + \
                            (cos(radians(ppts.rightangle)) * single_vector.y)

    backx = obj_position.x + ppts.distance * singleback_vector.x
    backy = obj_position.y + ppts.distance * singleback_vector.y

    backLamp = bpy.data.objects.get("TriLamp-Fill")
    backLamp.location = (backx, backy, ppts.height)

class LT_PT_Lights(bpy.types.PropertyGroup):
    name: StringProperty(
            name="name",
            default="key"
            ) # type: ignore
    type: StringProperty(
            name="type",
            default="AREA"
            ) # type: ignore
    
class LT_Properties(bpy.types.PropertyGroup):
    height: FloatProperty(
            name="Height",
            default=5
            ) # type: ignore
    distance: FloatProperty(
            name="Distance",
            default=5,
            min=0.1,
            subtype="DISTANCE"
            ) # type: ignore
    energy: IntProperty(
            name="Base Energy",
            default=50,
            min=1,
            update=update_energy
            ) # type: ignore
    contrast: IntProperty(
            name="Contrast",
            default=50,
            min=-100, max=100,
            subtype="PERCENTAGE"
            ) # type: ignore
    leftangle: IntProperty(
            name="Left Angle",
            default=26,
            min=1, max=180,
            subtype="ANGLE",
            update=update_left_angle
            ) # type: ignore
    rightangle: IntProperty(
            name="Right Angle",
            default=45,
            min=1, max=180,
            subtype="ANGLE",
            update=update_right_angle
            ) # type: ignore
    backangle: IntProperty(
            name="Back Angle",
            default=235,
            min=90, max=270,
            subtype="ANGLE",
            update=update_back_angle
            ) # type: ignore
    Light_Type_List = [
            ('POINT', "Point", "Point Light"),
            ('SUN', "Sun", "Sun Light"),
            ('SPOT', "Spot", "Spot Light"),
            ('AREA', "Area", "Area Light")
            ]
    primarytype: EnumProperty(
            attr='tl_type',
            name="Key Type",
            description="Choose the types of Key Lights you would like",
            items=Light_Type_List,
            default='AREA'
            ) # type: ignore
    secondarytype: EnumProperty(
            attr='tl_type',
            name="Fill + Back Type",
            description="Choose the types of secondary Lights you would like",
            items=Light_Type_List,
            default="AREA"
            ) # type: ignore
    

# Register all operators and menu
def register():
    bpy.utils.register_class(LT_OT_TriLighting)
    bpy.utils.register_class(LT_Properties)
    bpy.utils.register_class(LT_OP_Panel)
    bpy.utils.register_class(LT_PT_Lights)
    # bpy.types.VIEW3D_MT_light_add.append(menu_func)

    bpy.types.Scene.LightToolAttr = bpy.props.PointerProperty(type=LT_Properties)
    bpy.types.Scene.LT_lights = bpy.props.CollectionProperty(type=LT_Properties)

def unregister():
    bpy.utils.unregister_class(LT_OT_TriLighting)
    bpy.utils.unregister_class(LT_Properties)
    bpy.utils.unregister_class(LT_OP_Panel)
    bpy.utils.unregister_class(LT_PT_Lights)
    # bpy.types.VIEW3D_MT_light_add.remove(menu_func)

    del bpy.types.Scene.LightToolAttr
    del bpy.types.Scene.LT_lights

if __name__ == "__main__":
    register()
