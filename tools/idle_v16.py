"""Short camera drivers with a separate animated amplitude property."""
import bpy
def apply():
    cam=bpy.context.scene.camera;cam['V16_idle_blend']=1.0
    keys=[(0,1),(1026,1),(1050,1.8),(1272,1.8),(1296,1),(1701,1),(1725,1.8),(2001,1.8),(2025,1),(2619,1),(2643,1.8),(2676,1.8),(2700,1)]
    for frame,value in keys:
        cam['V16_idle_blend']=float(value);cam.keyframe_insert(data_path='["V16_idle_blend"]',frame=frame)
    cam.animation_data.action.name='V16_SMOOTH_IDLE_AMPLITUDE'
    for layer in cam.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='BEZIER';key.handle_left_type='AUTO_CLAMPED';key.handle_right_type='AUTO_CLAMPED'
    originals={('location',0):'0.0018*sin(frame/30*.91)+0.0006*sin(frame/30*1.73+.8)',('location',1):'0.0012*sin(frame/30*1.31)+0.0004*sin(frame/30*.43)',('location',2):'0.0007*sin(frame/30*1.08+.4)',('rotation_euler',0):'0.0007*sin(frame/30*.71+.9)',('rotation_euler',1):'0.0009*sin(frame/30*.63)',('rotation_euler',2):'0.0005*sin(frame/30*.49+.2)'}
    for fc in cam.animation_data.drivers:
        d=fc.driver
        for v in list(d.variables):d.variables.remove(v)
        v=d.variables.new();v.name='gain';v.type='SINGLE_PROP';v.targets[0].id=cam;v.targets[0].data_path='["V16_idle_blend"]'
        d.expression='('+originals[(fc.data_path,fc.array_index)]+')*gain'
        assert len(d.expression)<100
    bpy.context.scene.frame_set(0);print('V16_IDLE_DRIVER_FIXED',flush=True)
if __name__=='__main__':apply()
