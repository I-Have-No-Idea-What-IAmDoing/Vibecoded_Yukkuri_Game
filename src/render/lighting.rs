use bevy::{
    prelude::*,
    shader::ShaderRef,
    render::render_resource::AsBindGroup,
    sprite_render::{AlphaMode2d, Material2d, Material2dPlugin, MeshMaterial2d},
};
use bevy::prelude::Mesh2d;
use crate::ai::persistence::TimeElapsed;

#[derive(Component, Debug, Clone, Reflect)]
#[reflect(Component)]
pub struct LightSource {
    pub radius: f32,
    pub color: Color,
    pub intensity: f32,
    pub flicker_style: u32, // 0 = None, 1 = Fire, 2 = Pulse
    pub base_intensity: f32,
}

impl Default for LightSource {
    fn default() -> Self {
        Self {
            radius: 300.0,
            color: Color::WHITE,
            intensity: 1.0,
            flicker_style: 0,
            base_intensity: 1.0,
        }
    }
}

#[derive(Component)]
pub struct LightingOverlayMarker;

#[derive(Asset, TypePath, AsBindGroup, Debug, Clone)]
pub struct LightingMaterial {
    #[uniform(0)]
    pub ambient_color: Vec4,
    #[uniform(1)]
    pub num_lights: u32,
    #[uniform(2)]
    pub light_data: [Vec4; 64],
}

impl Material2d for LightingMaterial {
    fn fragment_shader() -> ShaderRef {
        "shaders/lighting.wgsl".into()
    }

    fn alpha_mode(&self) -> AlphaMode2d {
        AlphaMode2d::Blend
    }
}

#[derive(Resource, Debug, Default, Clone, Reflect)]
#[reflect(Resource, Default)]
pub struct CursorLightSettings {
    pub enabled: bool,
}

#[derive(Component)]
pub struct CursorLightMarker;

pub struct YukkuriLightingPlugin;

impl Plugin for YukkuriLightingPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins(Material2dPlugin::<LightingMaterial>::default())
            .init_resource::<CursorLightSettings>()
            .register_type::<LightSource>()
            .add_systems(Startup, (setup_lighting_system, setup_cursor_light_system))
            .add_systems(Update, (
                update_lighting_material_system,
                flicker_system,
                update_cursor_light_system,
            ));
    }
}

const AMBIENT_COLORS: [(f32, (u8, u8, u8)); 8] = [
    (0.0, (40, 40, 70)),  // Midnight
    (5.0, (40, 40, 70)),  // Early Morning
    (6.0, (100, 100, 120)),  // Dawn
    (8.0, (255, 255, 255)),  // Morning
    (17.0, (255, 255, 255)),  // Late Afternoon
    (19.0, (150, 100, 100)),  // Dusk
    (21.0, (60, 50, 80)),  // Evening
    (24.0, (40, 40, 70)),  // Midnight Loop
];

fn get_ambient_color(hour: f32) -> Vec4 {
    let t = hour.clamp(0.0, 24.0);
    
    let mut c1 = AMBIENT_COLORS[0];
    let mut c2 = AMBIENT_COLORS[0];
    
    for i in 0..AMBIENT_COLORS.len() - 1 {
        let t1 = AMBIENT_COLORS[i].0;
        let t2 = AMBIENT_COLORS[i + 1].0;
        if t >= t1 && t <= t2 {
            c1 = AMBIENT_COLORS[i];
            c2 = AMBIENT_COLORS[i + 1];
            break;
        }
    }
    
    let factor = if (c2.0 - c1.0).abs() > 0.001 {
        (t - c1.0) / (c2.0 - c1.0)
    } else {
        0.0
    };
    
    let rgb1 = c1.1;
    let rgb2 = c2.1;
    
    let r = rgb1.0 as f32 + (rgb2.0 as f32 - rgb1.0 as f32) * factor;
    let g = rgb1.1 as f32 + (rgb2.1 as f32 - rgb1.1 as f32) * factor;
    let b = rgb1.2 as f32 + (rgb2.2 as f32 - rgb1.2 as f32) * factor;
    
    let r_norm = r / 255.0;
    let g_norm = g / 255.0;
    let b_norm = b / 255.0;
    
    let brightness = (r_norm + g_norm + b_norm) / 3.0;
    let alpha = (1.0 - brightness).clamp(0.0, 0.85);
    
    Vec4::new(r_norm, g_norm, b_norm, alpha)
}

pub fn setup_lighting_system(
    mut commands: Commands,
    meshes: Option<ResMut<Assets<Mesh>>>,
    materials: Option<ResMut<Assets<LightingMaterial>>>,
) {
    let (Some(mut meshes), Some(mut materials)) = (meshes, materials) else {
        return;
    };

    let mesh = meshes.add(Rectangle::new(1.0, 1.0));
    let material = materials.add(LightingMaterial {
        ambient_color: Vec4::new(0.0, 0.0, 0.0, 0.0),
        num_lights: 0,
        light_data: [Vec4::ZERO; 64],
    });

    commands.spawn((
        Mesh2d(mesh),
        MeshMaterial2d(material),
        Transform::from_xyz(0.0, 0.0, 99.0)
            .with_scale(Vec3::new(10000.0, 10000.0, 1.0)),
        LightingOverlayMarker,
    ));
}

pub fn update_lighting_material_system(
    time_elapsed: Option<Res<TimeElapsed>>,
    query_lights: Query<(&GlobalTransform, &LightSource)>,
    materials: Option<ResMut<Assets<LightingMaterial>>>,
    query_material: Query<&MeshMaterial2d<LightingMaterial>>,
) {
    let Some(mut materials) = materials else {
        return;
    };

    let hour = time_elapsed.as_ref().map(|te| te.hour_of_day()).unwrap_or(12.0);
    let ambient_color = get_ambient_color(hour);

    let mut light_data = [Vec4::ZERO; 64];
    let mut num_lights = 0;

    for (g_trans, light) in query_lights.iter() {
        if light.intensity <= 0.0 {
            continue;
        }
        if num_lights >= 64 {
            break;
        }

        let pos = g_trans.translation().xy();
        light_data[num_lights] = Vec4::new(pos.x, pos.y, light.radius, light.intensity);
        num_lights += 1;
    }

    for mat_handle in query_material.iter() {
        if let Some(mut mat) = materials.get_mut(mat_handle) {
            mat.ambient_color = ambient_color;
            mat.num_lights = num_lights as u32;
            mat.light_data = light_data;
        }
    }
}

pub fn flicker_system(
    time_elapsed: Option<Res<TimeElapsed>>,
    mut query: Query<&mut LightSource>,
) {
    let t = time_elapsed.map(|te| te.elapsed).unwrap_or(0.0);
    
    for mut light in query.iter_mut() {
        match light.flicker_style {
            1 => {
                let noise = (t * 10.0).sin() * 0.1
                    + (t * 23.0).sin() * 0.05
                    + (t * 47.0).sin() * 0.02;
                light.intensity = light.base_intensity * (1.0 + noise);
            }
            2 => {
                light.intensity = light.base_intensity * (0.8 + 0.2 * (t * std::f32::consts::PI).sin());
            }
            _ => {
                light.intensity = light.base_intensity;
            }
        }
    }
}

pub fn setup_cursor_light_system(mut commands: Commands) {
    commands.spawn((
        Transform::default(),
        LightSource {
            radius: 300.0,
            color: Color::WHITE,
            intensity: 0.0,
            flicker_style: 0,
            base_intensity: 0.8,
        },
        CursorLightMarker,
    ));
}

pub fn update_cursor_light_system(
    cursor_light_settings: Res<CursorLightSettings>,
    window_query: Query<&Window, With<bevy::window::PrimaryWindow>>,
    camera_query: Query<(&Camera, &GlobalTransform), With<crate::camera::MainCamera>>,
    mut query_cursor_light: Query<(&mut Transform, &mut LightSource), With<CursorLightMarker>>,
) {
    let Some(window) = window_query.iter().next() else { return; };
    let Some((camera, camera_transform)) = camera_query.iter().next() else { return; };
    let Some(cursor_position) = window.cursor_position() else { return; };
    let Ok(world_pos) = camera.viewport_to_world_2d(camera_transform, cursor_position) else { return; };

    for (mut transform, mut light) in query_cursor_light.iter_mut() {
        transform.translation = world_pos.extend(transform.translation.z);
        light.intensity = if cursor_light_settings.enabled {
            light.base_intensity
        } else {
            0.0
        };
    }
}
