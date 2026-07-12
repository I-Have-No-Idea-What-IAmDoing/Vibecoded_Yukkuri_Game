struct FragmentInput {
    @location(0) world_position: vec4<f32>,
    @location(2) uv: vec2<f32>,
};

@group(2) @binding(0)
var<uniform> ambient_color: vec4<f32>;

@group(2) @binding(1)
var<uniform> num_lights: u32;

@group(2) @binding(2)
var<uniform> light_data: array<vec4<f32>, 64>;

@fragment
fn fragment(input: FragmentInput) -> @location(0) vec4<f32> {
    let pixel_pos = input.world_position.xy;
    var light_sum: f32 = 0.0;

    for (var i: u32 = 0u; i < num_lights; i = i + 1u) {
        let light = light_data[i];
        let light_pos = light.xy;
        let radius = light.z;
        let intensity = light.w;

        let dist = distance(pixel_pos, light_pos);
        if (dist < radius) {
            let factor = (1.0 - (dist / radius)) * intensity;
            light_sum = light_sum + factor;
        }
    }

    // Smoothly subtract the light intensity from the darkness alpha
    let final_alpha = max(0.0, ambient_color.a - light_sum);
    
    // Return ambient color with final alpha
    return vec4<f32>(ambient_color.rgb, final_alpha);
}
