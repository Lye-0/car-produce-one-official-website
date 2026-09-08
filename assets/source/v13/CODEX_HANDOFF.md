# CPO v13 — editing handoff

## Primary files
- `CAR_PRODUCE_ONE_ANIMATED_v13.glb`: actual integrated, animated asset; reference frame retains the old glTF Y-up root conversion.
- `animation/timeline.json`: route annotations, timing, authored camera and clip identifiers.
- `source/build_v13.py`: procedural source; takes the original v12 path as argv[1]. Requires the v12 base, not shipped redundantly in this package.
- `source/vehicles.py`: ORIGINAL approximate coupe/SUV meshes, not licensed Honda CAD.
- `web/player.js`: dependency-free GLB parser, TRS evaluator, review renderer, scroll/time controller, LCD-to-HTML demonstration.
- `OPEN_IN_BLENDER.py`: new scene + importer + camera/fps setup, not executed here.

## Contract to retain
Source coordinate frame is X right, +Y into shop, +Z up. The main camera is a real glTF perspective camera at `CPO_CINEMATIC_CAMERA`. Storefront is near Y=-1.50m. Preserve 10cm file-unit wall strip, reduced/repositioned printer, 1.5m entrance extension, sign center/corner fixes, and main furniture.

Main clip `CPO_MASTER_90s` includes the camera, arrival car translation and wheels, passenger door and two folding entrance leaves. Idle clip `CPO_IDLE_CITY_LOOP` is independently timed. Do not activate both at arbitrary weights. For the Web idle transition retain the current city X offset while starting main time at zero. Store-side lamp posts remain static, so a captured loop phase cannot put a light post inside the entrance.

The two glass leaves have animated pivot groups. Their existing parents have a -1.5m Y translation! Child matrices are localised to the new hinges. Do not reintroduce the earlier world/local pivot error.

GLB animation samplers refer to numeric accessors; texture samplers are also explicit. Retain explicit texture sampler objects for compatibility with the user's Blender importer.

## Authored moves
Only the agreed four small-furniture groups are moved; see JSON. Original vertex streams are retained for all 2,951 base mesh nodes. This does NOT imply all object world positions are unchanged: moving furniture and animated leaf transforms are deliberate. The PC screen material is the only replacement on an existing interior surface.

## Route / rendering
The route is baked at 30fps. PCHIP position segments + eased endpoints and signed continuous quaternions. Tools hold 38–48%, magazine hold 63–75%. Walking stops at 90%; final camera lean is cinematic rather than a full human capsule passing over a desk. End eye stays 0.275m ahead of the LCD. Web projects the actual LCD quad into the HTML overlay before fading into the sample page.

Collision tests are SAMPLED, not continuous formal proof. Static walking uses actual-mesh height-band projected footprints; broad wall/counter polygons use unions so apertures are not falsely blocked. Head checks during exit use a smaller sphere; this is not full body inverse kinematics. Keep human route direction/height natural and re-test with high-detail replacement cars.

## Known refinement needs
Vehicle surfacing is an approximate blockout-to-mid-detail model and is visually below production automotive rendering quality. Replace/refine geometry under the same roots/pivots, preserving realistic dimensions and mirror envelopes. Detailed vehicle interiors, exact lamps, labels, and Honda-certified surfaces are not provided.

Lighting/transmission in the self-contained WebGL renderer and VTK movie are review approximations. No end-to-end actual WebGL GPU or Blender application test was possible here. Native shader compilation and mocked-GPU JS pose/UI tests are explicitly labelled. Do not turn those into claims of a browser/Blender render pass.

The 800x500 8fps MP4 is a motion/continuity review, NOT final 30/60fps video. Main GLB has 30fps sampled animation and interpolates between keys. The final company website information and live reservation/contact functionality are not implemented: the HTML section is a transition demo.

## Delivering a production follow-up
Use Blender to create/save the `.blend` source after import, make the route editable as a spline/rig, verify display of all imported animation actions, upgrade materials/car meshes, test real desktop/mobile browsers, and export final image sequences or optimise real-time playback. No public deployment has been performed.
