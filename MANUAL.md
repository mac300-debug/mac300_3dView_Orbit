# Mac300 Viewport Orbit - Detailed User Manual

This manual provides an in-depth explanation of every setting, UI panel control, and advanced feature available in the **Mac300 Viewport Orbit** add-on (v2.2.0).

---

## 📍 Panel Location

Once installed and enabled, the add-on UI is located in the **3D Viewport Sidebar** (the "N-Panel"). 
1. Open the 3D Viewport.
2. Press `N` on your keyboard to toggle the sidebar.
3. Click on the **Orbit** tab on the right side.
4. You will see the **Orbit Director** panel.

---

## 🎛️ Settings & Controls

### 1. Master Controls

- **Start / Stop Director:** 
  - Starts or stops the background viewport rotation. When running, the panel will display a pause icon and say **Stop Director**. When idle, it shows a play icon and says **Start Director**.
- **Master Speed:**
  - Controls the rotation speed per tick. 
  - **Tip:** You can set negative values (e.g. `-0.015`) to reverse the rotation direction.
- **Blend Time (s):**
  - Defines the duration in seconds for smooth interpolation. This setting is shared across two animation events:
    1. **Axis transitions:** The duration it takes to smoothly sweep from one rotation axis (e.g. Z) into another (e.g. X).
    2. **Auto-Framing transitions:** The duration it takes to zoom/pan to a new focus target.
  - If set to `0.0`, changes will snap instantly.

---

### 2. Orbit Modes

You can choose from three distinct director modes to drive the camera:

#### A. Static Mode (Single Axis)
- **Axis (X, Y, Z):** Rotates the viewport continuously around the selected global world axis.

#### B. Playlist Mode
- Create a scripted sequence of viewport rotation steps.
- **Add / Remove Buttons:** Click `+` to add a new step, or `-` to delete the selected step.
- **Playlist Table:**
  - **Axis:** Choose which axis to rotate around for this step.
  - **Seconds (s):** Set how long this step lasts before transitioning to the next step.
- **Play Indicator:** When running, the active step is highlighted with a message showing the active index (e.g., `Currently Playing: Index 1`). The list will automatically loop back to the beginning after the last step.

#### C. Random Mode
- Procedurally sweeps through random axes at random time intervals.
- **Min Time / Max Time:** Controls the minimum and maximum boundaries (in seconds) for how long each random axis phase lasts before a new axis is chosen.

---

### 3. Cinematic Auto-Framing

Auto-Framing automatically centers and zooms the viewport camera on your workspace objects, preventing your model from drifting out of view during long orbits.

- **Auto-Framing (Checkbox):** Toggles the feature on and off. (Note: Only runs when Blender is in **Object Mode**).
- **Trigger Every (s):** The interval in seconds between auto-framing events.
- **% Chance to Focus Selected:**
  - A slider from `0%` to `100%`.
  - Determines the probability of focusing on the selected object(s) vs. focusing on the entire scene.
  - *Example:* If set to `70%`, there is a 70% chance it will zoom in on your selected mesh, and a 30% chance it will zoom out to frame all objects in the scene.
- **Framing Zoom:**
  - The zoom multiplier for the camera.
  - Lower values (e.g., `0.8`) frame the target closer.
  - Higher values (e.g., `1.5`) leave more margin around the object.

> [!NOTE]
> **Under the Hood - The Phantom Operator Trick:**
> Viewport calculation in Blender is usually instant and jarring. To keep the viewport movement completely smooth, the plugin uses a background "Phantom Operator" trick:
> 1. It saves the camera's current position and zoom.
> 2. It overrides Blender's context and runs a native frame-selected or frame-all operator in a single frame.
> 3. It grabs the new coordinates Blender calculated.
> 4. It immediately restores the viewport to its original coordinates before the screen redraws.
> 5. It uses a mathematical `lerp` (linear interpolation) with ease-in/ease-out curves to glide the camera to the target coordinates over your specified **Blend Time**.

---

## ⚡ Standalone Script Mode

If you do not want to install the full add-on package, we have included a lightweight script: `viewport_orbit_standalone.py`.

### How to use it:
1. Open the **Text Editor** area in Blender.
2. Click **Open** and select `viewport_orbit_standalone.py`.
3. Click the **Run Script** (Play) button in the Text Editor header.
4. Open the `View3D` sidebar (`N`) ➔ **Orbit** tab ➔ **Viewport Orbit** panel.
5. This standalone version offers simple X, Y, or Z rotation without playlist sequencing or auto-framing.

---

## 🎬 Recording Tips for Content Creators

To record stunning, professional videos of your models using this plugin:

1. **Clean Viewport:** Press `Shift + Alt + Z` in the 3D viewport to toggle off all UI overlays (grids, 3D cursor, outlines, gizmos).
2. **Viewport Shading:** Set your viewport shading to **Rendered** or **Material Preview** for high-quality visuals.
3. **Smooth Sweeps:** Set your **Blend Time** between `1.5` and `3.0` seconds to create elegant, slow sweeps when the auto-framer triggers or the playlist changes direction.
4. **Slow Rotation:** Keep **Master Speed** low (e.g., `0.01` to `0.02`) for a premium showcase feel. Negative speeds are great for reversing direction when switching axes.
