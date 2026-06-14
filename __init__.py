# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 MAC300 (www.mac300.pl)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

bl_info = {
    "name": "Mac300_Viewport_Orbit",
    "author": "MAC300",
    "version": (2, 2, 0),
    "blender": (5, 1, 2),
    "location": "View3D > Sidebar > Orbit",
    "description": "Cinematic viewport orbiting with playlists, randomizers, and fully smooth auto-framing.",
    "doc_url": "www.mac300.pl",
    "category": "3D View",
    "type": "add-on",
}

import bpy
import mathutils
import time
import random
import bpy.utils.previews

# =========================================================================
# Global State Trackers
# =========================================================================
_orbit_timer_registered = False
_target_window_ptr = 0
preview_collections = {}

# Timing & Director variables
_phase_start_time = 0.0
_phase_duration = 5.0
_playlist_index = 0
_frame_last_time = 0.0

# Smooth Axis Transition variables
_current_axis = mathutils.Vector((0.0, 0.0, 1.0))
_target_axis = mathutils.Vector((0.0, 0.0, 1.0))
_previous_axis = mathutils.Vector((0.0, 0.0, 1.0))
_is_transitioning = False
_transition_start_time = 0.0

# Smooth Auto-Framing Transition variables
_is_framing = False
_frame_start_loc = mathutils.Vector((0.0, 0.0, 0.0))
_frame_target_loc = mathutils.Vector((0.0, 0.0, 0.0))
_frame_start_dist = 10.0
_frame_target_dist = 10.0
_frame_anim_start_time = 0.0


def get_axis_vector(axis_char):
    """Returns mathutils Vector for blending"""
    if axis_char == 'X': return mathutils.Vector((1.0, 0.0, 0.0))
    elif axis_char == 'Y': return mathutils.Vector((0.0, 1.0, 0.0))
    return mathutils.Vector((0.0, 0.0, 1.0))


def trigger_auto_frame(scene):
    """The 'Phantom Operator' trick to calculate zoom coordinates"""
    global _is_framing, _frame_start_loc, _frame_target_loc
    global _frame_start_dist, _frame_target_dist, _frame_anim_start_time
    
    for window in bpy.context.window_manager.windows:
        if window.as_pointer() == _target_window_ptr and window.screen:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            # Get the 3D space data
                            space = area.spaces.active
                            rv3d = space.region_3d
                            if not rv3d: continue

                            # 1. Save current camera position/zoom
                            _frame_start_loc = rv3d.view_location.copy()
                            _frame_start_dist = rv3d.view_distance

                            # 2. Phantom Execution (Forces Blender to do the complex frustum math instantly)
                            is_selected_frame = False
                            with bpy.context.temp_override(window=window, area=area, region=region):
                                run_selected = False
                                if random.random() <= (scene.orbit_frame_selected_chance / 100.0):
                                    if bpy.context.mode == 'OBJECT':
                                        if len(bpy.context.selected_objects) > 0:
                                            run_selected = True
                                    elif bpy.context.mode == 'EDIT_MESH':
                                        active_obj = bpy.context.active_object
                                        if active_obj and active_obj.type == 'MESH':
                                            import bmesh
                                            try:
                                                bm = bmesh.from_edit_mesh(active_obj.data)
                                                if any(v.select for v in bm.verts):
                                                    run_selected = True
                                            except Exception:
                                                pass
                                    else:
                                        if bpy.context.active_object:
                                            run_selected = True

                                if run_selected:
                                    try:
                                        bpy.ops.view3d.view_selected()
                                        is_selected_frame = True
                                    except: pass
                                else:
                                    try: bpy.ops.view3d.view_all()
                                    except: pass

                            # 3. Steal the calculated target coordinates
                            _frame_target_loc = rv3d.view_location.copy()
                            _frame_target_dist = rv3d.view_distance
                            if is_selected_frame:
                                _frame_target_dist *= scene.orbit_frame_zoom_factor

                            # 4. Revert immediately so the user doesn't see a jump
                            rv3d.view_location = _frame_start_loc
                            rv3d.view_distance = _frame_start_dist

                            # 5. Trigger our smooth lerp animation
                            _is_framing = True
                            _frame_anim_start_time = time.time()
                            
                            return # Only need to calculate this once per screen!


def viewport_orbit_timer_callback():
    """Background timer running the cinematic logic"""
    scene = bpy.context.scene
    
    if not scene.viewport_orbit_running:
        global _orbit_timer_registered
        _orbit_timer_registered = False
        return None
        
    global _phase_start_time, _phase_duration, _playlist_index, _frame_last_time
    global _current_axis, _target_axis, _previous_axis, _is_transitioning, _transition_start_time
    global _is_framing, _frame_start_loc, _frame_target_loc, _frame_start_dist, _frame_target_dist, _frame_anim_start_time
    
    now = time.time()
    elapsed = now - _phase_start_time
    desired_axis = _target_axis
    
    # ==========================================
    # 1. DIRECTOR LOGIC (Determine desired axis)
    # ==========================================
    if scene.orbit_mode == 'SINGLE':
        desired_axis = get_axis_vector(scene.viewport_orbit_axis)
        
    elif scene.orbit_mode == 'PLAYLIST':
        items = scene.orbit_playlist
        if len(items) > 0:
            current_item = items[_playlist_index]
            if elapsed >= current_item.duration:
                _playlist_index = (_playlist_index + 1) % len(items)
                _phase_start_time = now
            desired_axis = get_axis_vector(items[_playlist_index].axis)
            
    elif scene.orbit_mode == 'RANDOM':
        if elapsed >= _phase_duration:
            desired_axis = get_axis_vector(random.choice(['X', 'Y', 'Z']))
            _phase_duration = random.uniform(scene.orbit_random_min, scene.orbit_random_max)
            _phase_start_time = now

    # ==========================================
    # 2. AXIS TRANSITION LOGIC
    # ==========================================
    if desired_axis != _target_axis:
        _previous_axis = _current_axis.copy()
        _target_axis = desired_axis.copy()
        _is_transitioning = True
        _transition_start_time = now

    if _is_transitioning:
        t = 1.0
        if scene.orbit_transition_time > 0:
            t = (now - _transition_start_time) / scene.orbit_transition_time
            
        if t >= 1.0:
            _is_transitioning = False
            _current_axis = _target_axis.copy()
        else:
            ease_t = t * t * (3.0 - 2.0 * t)
            _current_axis = _previous_axis.lerp(_target_axis, ease_t).normalized()

    # ==========================================
    # 3. AUTO-FRAMING TRIGGER
    # ==========================================
    if scene.orbit_auto_frame and bpy.context.mode == 'OBJECT':
        if now - _frame_last_time >= scene.orbit_frame_interval:
            _frame_last_time = now
            trigger_auto_frame(scene)

    # ==========================================
    # 4. AUTO-FRAMING TRANSITION LOGIC
    # ==========================================
    ease_f = 1.0
    t_frame = 1.0
    if _is_framing:
        if scene.orbit_transition_time > 0:
            t_frame = (now - _frame_anim_start_time) / scene.orbit_transition_time
        ease_f = t_frame * t_frame * (3.0 - 2.0 * t_frame) if t_frame < 1.0 else 1.0

    # ==========================================
    # 5. APPLY ALL TRANSFORMATIONS
    # ==========================================
    for window in bpy.context.window_manager.windows:
        if window.as_pointer() == _target_window_ptr and window.screen:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            rv3d = space.region_3d
                            if rv3d:
                                # Apply Continuous Rotation
                                rot = mathutils.Quaternion(_current_axis, scene.viewport_orbit_speed)
                                rv3d.view_rotation = rot @ rv3d.view_rotation
                                
                                # Apply Smooth Camera Zoom/Pan
                                if _is_framing:
                                    if t_frame >= 1.0:
                                        rv3d.view_location = _frame_target_loc
                                        rv3d.view_distance = _frame_target_dist
                                        _is_framing = False
                                    else:
                                        rv3d.view_location = _frame_start_loc.lerp(_frame_target_loc, ease_f)
                                        rv3d.view_distance = _frame_start_dist + (_frame_target_dist - _frame_start_dist) * ease_f

                    area.tag_redraw()
            
    return 0.02 

# =========================================================================
# Playlist Data & UI
# =========================================================================

class VIEWPORT_ORBIT_PropertyGroup(bpy.types.PropertyGroup):
    axis: bpy.props.EnumProperty(
        items=[('X', "X Axis", ""), ('Y', "Y Axis", ""), ('Z', "Z Axis", "")],
        default='Z'
    )
    duration: bpy.props.FloatProperty(name="Seconds", default=5.0, min=0.5)

class VIEWPORT_ORBIT_UL_playlist(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "axis", text="")
        row.prop(item, "duration", text="s")

class VIEWPORT_ORBIT_OT_playlist_add(bpy.types.Operator):
    bl_idname = "view3d.orbit_playlist_add"
    bl_label = "Add"
    def execute(self, context):
        context.scene.orbit_playlist.add()
        context.scene.orbit_playlist_index = len(context.scene.orbit_playlist) - 1
        return {'FINISHED'}

class VIEWPORT_ORBIT_OT_playlist_remove(bpy.types.Operator):
    bl_idname = "view3d.orbit_playlist_remove"
    bl_label = "Remove"
    def execute(self, context):
        idx = context.scene.orbit_playlist_index
        if 0 <= idx < len(context.scene.orbit_playlist):
            context.scene.orbit_playlist.remove(idx)
            context.scene.orbit_playlist_index = min(max(0, idx - 1), len(context.scene.orbit_playlist) - 1)
        return {'FINISHED'}

# =========================================================================
# Main Operators
# =========================================================================

class VIEWPORT_ORBIT_OT_toggle(bpy.types.Operator):
    """Start or Stop the viewport orbit rotation"""
    bl_idname = "view3d.toggle_viewport_orbit"
    bl_label = "Toggle Viewport Orbit"
    
    def execute(self, context):
        scene = context.scene
        scene.viewport_orbit_running = not scene.viewport_orbit_running
        
        if scene.viewport_orbit_running:
            global _orbit_timer_registered, _target_window_ptr
            global _phase_start_time, _playlist_index, _frame_last_time, _phase_duration
            global _current_axis, _target_axis
            
            _target_window_ptr = context.window.as_pointer()
            _phase_start_time = time.time()
            _frame_last_time = time.time()
            _playlist_index = 0
            _phase_duration = random.uniform(scene.orbit_random_min, scene.orbit_random_max)
            
            # Reset axes based on starting mode
            start_axis_char = 'Z'
            if scene.orbit_mode == 'SINGLE': start_axis_char = scene.viewport_orbit_axis
            elif scene.orbit_mode == 'PLAYLIST' and len(scene.orbit_playlist) > 0: start_axis_char = scene.orbit_playlist[0].axis
            elif scene.orbit_mode == 'RANDOM': start_axis_char = random.choice(['X', 'Y', 'Z'])
            
            _current_axis = get_axis_vector(start_axis_char)
            _target_axis = _current_axis.copy()
            
            if not _orbit_timer_registered:
                _orbit_timer_registered = True
                bpy.app.timers.register(viewport_orbit_timer_callback)
        return {'FINISHED'}

# =========================================================================
# UI Panel
# =========================================================================

class VIEWPORT_ORBIT_PT_panel(bpy.types.Panel):
    bl_label = "Orbit Director"
    bl_idname = "VIEWPORT_ORBIT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Orbit'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Dynamic Preview Banner Loading
        pcoll = preview_collections.get("main")
        if pcoll and "orbit_banner" in pcoll:
            icon = pcoll["orbit_banner"]
            # Draw the banner at the top of the panel, centered and scaled
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.template_icon(icon_value=icon.icon_id, scale=10.0)
            layout.separator()

        # Play/Stop Button
        row = layout.row()
        row.scale_y = 1.5
        if scene.viewport_orbit_running:
            row.operator("view3d.toggle_viewport_orbit", text="Stop Director", icon='PAUSE')
        else:
            row.operator("view3d.toggle_viewport_orbit", text="Start Director", icon='PLAY')

        layout.separator()
        layout.prop(scene, "viewport_orbit_speed", text="Master Speed")
        layout.prop(scene, "orbit_transition_time", text="Blend Time (s)", icon='ANIM')
        
        layout.separator()
        layout.prop(scene, "orbit_mode", text="Mode")

        # Dynamic UI based on mode
        box = layout.box()
        if scene.orbit_mode == 'SINGLE':
            box.prop(scene, "viewport_orbit_axis", text="Axis")
            
        elif scene.orbit_mode == 'PLAYLIST':
            row = box.row()
            row.template_list("VIEWPORT_ORBIT_UL_playlist", "", scene, "orbit_playlist", scene, "orbit_playlist_index")
            col = row.column(align=True)
            col.operator("view3d.orbit_playlist_add", icon='ADD', text="")
            col.operator("view3d.orbit_playlist_remove", icon='REMOVE', text="")
            
            if scene.viewport_orbit_running:
                box.label(text=f"Currently Playing: Index {(_playlist_index + 1)}", icon='TIME')
                
        elif scene.orbit_mode == 'RANDOM':
            box.label(text="Randomize axis every X seconds:")
            col = box.column(align=True)
            col.prop(scene, "orbit_random_min", text="Min Time")
            col.prop(scene, "orbit_random_max", text="Max Time")

        # Auto-Framing UI
        layout.separator()
        frame_box = layout.box()
        frame_box.prop(scene, "orbit_auto_frame", text="Auto-Framing", icon='VIEW_CAMERA')
        
        if scene.orbit_auto_frame:
            frame_box.prop(scene, "orbit_frame_interval", text="Trigger Every (s)")
            frame_box.prop(scene, "orbit_frame_selected_chance", text="% Chance to Focus Selected", slider=True)
            frame_box.prop(scene, "orbit_frame_zoom_factor", text="Framing Zoom")


# =========================================================================
# Registration
# =========================================================================

classes = (
    VIEWPORT_ORBIT_PropertyGroup,
    VIEWPORT_ORBIT_UL_playlist,
    VIEWPORT_ORBIT_OT_playlist_add,
    VIEWPORT_ORBIT_OT_playlist_remove,
    VIEWPORT_ORBIT_OT_toggle,
    VIEWPORT_ORBIT_PT_panel,
)

def register():
    # Initialize and load preview icons/banners
    pcoll = bpy.utils.previews.new()
    import os
    addon_dir = os.path.dirname(__file__)
    img_path = os.path.join(addon_dir, "orbit_banner.png")
    if os.path.exists(img_path):
        pcoll.load("orbit_banner", img_path, 'IMAGE')
    preview_collections["main"] = pcoll

    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.viewport_orbit_running = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.viewport_orbit_speed = bpy.props.FloatProperty(default=0.015, min=-0.5, max=0.5, step=0.1, precision=4)
    
    # Shared blend time for both rotation curves and auto-framing movements
    bpy.types.Scene.orbit_transition_time = bpy.props.FloatProperty(
        name="Blend Time", description="How long it takes to smoothly sweep into a new axis or frame",
        default=2.0, min=0.0, max=10.0, step=10, precision=1
    )
    
    # Mode Toggle
    bpy.types.Scene.orbit_mode = bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('SINGLE', "Static", "Rotate on one axis"),
            ('PLAYLIST', "Playlist", "Cycle through a list of axes and timings"),
            ('RANDOM', "Random", "Randomly pick axis and timings"),
        ],
        default='SINGLE'
    )
    
    # Single Mode
    bpy.types.Scene.viewport_orbit_axis = bpy.props.EnumProperty(
        items=[('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")], default='Z'
    )
    
    # Playlist Mode
    bpy.types.Scene.orbit_playlist = bpy.props.CollectionProperty(type=VIEWPORT_ORBIT_PropertyGroup)
    bpy.types.Scene.orbit_playlist_index = bpy.props.IntProperty(name="Index")
    
    # Random Mode
    bpy.types.Scene.orbit_random_min = bpy.props.FloatProperty(default=5.0, min=1.0)
    bpy.types.Scene.orbit_random_max = bpy.props.FloatProperty(default=15.0, min=1.0)
    
    # Auto-Framing
    bpy.types.Scene.orbit_auto_frame = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.orbit_frame_interval = bpy.props.FloatProperty(default=10.0, min=1.0)
    bpy.types.Scene.orbit_frame_selected_chance = bpy.props.IntProperty(default=50, min=0, max=100)
    bpy.types.Scene.orbit_frame_zoom_factor = bpy.props.FloatProperty(
        name="Framing Zoom",
        description="Zoom multiplier for selected framing (lower values zoom in closer, higher values zoom out further)",
        default=1.0,
        min=0.01,
        max=100.0
    )

def unregister():
    # Stop execution if running
    try:
        bpy.context.scene.viewport_orbit_running = False
    except Exception:
        pass
        
    # Clean up preview collection
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
    props = [
        "viewport_orbit_running", "viewport_orbit_speed", "orbit_transition_time", "orbit_mode", 
        "viewport_orbit_axis", "orbit_playlist", "orbit_playlist_index", 
        "orbit_random_min", "orbit_random_max", "orbit_auto_frame", 
        "orbit_frame_interval", "orbit_frame_selected_chance", "orbit_frame_zoom_factor"
    ]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)
            
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()