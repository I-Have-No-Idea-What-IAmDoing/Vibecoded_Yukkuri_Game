use bevy::prelude::*;
use crate::camera::MainCamera;

#[derive(Component, Reflect, Debug, Clone, PartialEq, Eq, Default)]
#[reflect(Component, Default)]
pub struct LODComponent {
    pub level: u32,
}

pub struct LODPlugin;

impl Plugin for LODPlugin {
    fn build(&self, app: &mut App) {
        app.register_type::<LODComponent>()
            .add_systems(Update, lod_update_system);
    }
}

pub fn lod_update_system(
    camera_query: Query<(&Camera, &GlobalTransform), With<MainCamera>>,
    mut query: Query<(&Transform, &mut LODComponent)>,
) {
    let Some((_camera, camera_transform)) = camera_query.iter().next() else { return; };
    let camera_pos = camera_transform.translation().truncate();
    
    let l1_sq = 600.0 * 600.0;
    let l2_sq = 1200.0 * 1200.0;
    let l3_sq = 2400.0 * 2400.0;
    
    for (transform, mut lod) in query.iter_mut() {
        let dist_sq = transform.translation.truncate().distance_squared(camera_pos);
        if dist_sq < l1_sq {
            lod.level = 0;
        } else if dist_sq < l2_sq {
            lod.level = 1;
        } else if dist_sq < l3_sq {
            lod.level = 2;
        } else {
            lod.level = 3;
        }
    }
}
