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
    
    let high_dist_sq = 800.0 * 800.0;
    let med_dist_sq = 1500.0 * 1500.0;
    
    for (transform, mut lod) in query.iter_mut() {
        let dist_sq = transform.translation.truncate().distance_squared(camera_pos);
        if dist_sq < high_dist_sq {
            lod.level = 0;
        } else if dist_sq < med_dist_sq {
            lod.level = 1;
        } else {
            lod.level = 2;
        }
    }
}
