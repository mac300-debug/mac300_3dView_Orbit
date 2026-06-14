bl_info = {
    "name": "Viewport Orbit Recorder",
    "author": "mac300",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Orbit",
    "description": "Smoothly orbits the 3D viewport for recording workflows.",
    "category": "3D View",
}

import bpy
import mathutils

# Global tracker to prevent multiple timers from running simultaneously
_orbit_timer_registered = False
_target_window_ptr = 0

def viewport_orbit_timer_callback():
    """Background timer to smoothly rotate the viewport region_3d"""
    scene = bpy.context.scene
    
    # Exit timer if orbit state is disabled
    if not scene.viewport_orbit_running:
        global _orbit_timer_registered
        _orbit_timer_registered = False
        return None
        
    speed = scene.viewport_orbit_speed
    axis_selection = scene.viewport_orbit_axis
    
    # Determine rotation axis based on UI selection
    axis = (0.0, 0.0, 1.0) # Default Z
    if axis_selection == 'X':
        axis = (1.0, 0.0, 0.0)
    elif axis_selection == 'Y':
        axis = (0.0, 1.0, 0.0)
        
    # Rotate View3D spaces
    for window in bpy.context.window_manager.windows:
        if window.as_pointer() == _target_window_ptr and window.screen:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            rv3d = space.region_3d
                            if rv3d:
                                # Apply quaternion rotation
                                rot = mathutils.Quaternion(axis, speed)
                                rv3d.view_rotation = rot @ rv3d.view_rotation
                    area.tag_redraw()
            
    # Run every 20ms (approx 50 fps) for smooth recording
    return 0.02 

# =========================================================================
# Operators
# =========================================================================

class VIEWPORT_ORBIT_OT_toggle(bpy.types.Operator):
    """Start or Stop the viewport orbit rotation"""
    bl_idname = "view3d.toggle_viewport_orbit"
    bl_label = "Toggle Viewport Orbit"
    
    def execute(self, context):
        scene = context.scene
        
        # Toggle the running state
        scene.viewport_orbit_running = not scene.viewport_orbit_running
        
        if scene.viewport_orbit_running:
            global _orbit_timer_registered, _target_window_ptr
            _target_window_ptr = context.window.as_pointer()
            if not _orbit_timer_registered:
                _orbit_timer_registered = True
                bpy.app.timers.register(viewport_orbit_timer_callback)
            self.report({'INFO'}, "Viewport Orbit Started")
        else:
            self.report({'INFO'}, "Viewport Orbit Stopped")
            
        return {'FINISHED'}

# =========================================================================
# UI Panel
# =========================================================================

class VIEWPORT_ORBIT_PT_panel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport Sidebar"""
    bl_label = "Viewport Orbit"
    bl_idname = "VIEWPORT_ORBIT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Orbit' # Creates a dedicated tab named "Orbit"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Play/Stop Button
        row = layout.row()
        row.scale_y = 1.5
        if scene.viewport_orbit_running:
            row.operator("view3d.toggle_viewport_orbit", text="Stop Orbit", icon='PAUSE')
        else:
            row.operator("view3d.toggle_viewport_orbit", text="Start Orbit", icon='PLAY')

        # Settings
        layout.separator()
        layout.prop(scene, "viewport_orbit_speed", text="Speed")
        layout.prop(scene, "viewport_orbit_axis", text="Axis")

# =========================================================================
# Registration
# =========================================================================

classes = (
    VIEWPORT_ORBIT_OT_toggle,
    VIEWPORT_ORBIT_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.viewport_orbit_running = bpy.props.BoolProperty(default=False)
    
    # Adjustable parameters
    bpy.types.Scene.viewport_orbit_speed = bpy.props.FloatProperty(
        name="Orbit Speed",
        description="Speed of the rotation per tick. Negative values reverse direction",
        default=0.015,
        min=-0.5,
        max=0.5,
        step=0.1,
        precision=4
    )
    
    bpy.types.Scene.viewport_orbit_axis = bpy.props.EnumProperty(
        name="Orbit Axis",
        description="World axis to orbit around",
        items=[
            ('X', "X Axis", "Orbit around the X axis"),
            ('Y', "Y Axis", "Orbit around the Y axis"),
            ('Z', "Z Axis", "Orbit around the Z axis"),
        ],
        default='Z'
    )

def unregister():
    # Stop timer on unregister to prevent memory leaks or crashes
    bpy.context.scene.viewport_orbit_running = False
    
    del bpy.types.Scene.viewport_orbit_running
    del bpy.types.Scene.viewport_orbit_speed
    del bpy.types.Scene.viewport_orbit_axis
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()