# Proposal: Weather, Seasons & Temperature

## Overview
Transform the environment into a dynamic system that dictates gameplay rhythms. Players must adapt to changing seasons and protect Yukkuris from the elements.

## 1. Dynamic Weather System
Weather is no longer just visual; it is a physical force.

### Weather States
- **Cloudy**: Standard state. No effects.
- **Sunny**: Bonus to `Happiness` regeneration. Yukkuris will be able to sunbathe.
- **Rainy**:
    - *Visual*: Dark screen tint, drawing rain particles (Count: >500).
    - *Effect*: Puddles form on the ground.
    - *Impact*: Yukkuris get "Wet" status (Cooling). High `Stress` if they hate water.
    - *Behavior*: Yukkuris will seek shelter.
    - *Impact*: Yukkuri will get hurt if they stay in the rain for too long and melt.
- **Thunderstorm**:
    - *Visual*: Intense rain, random full-screen white flashes (Lightning).
    - *Audio*: Delayed thunder sounds.
    - *Impact*: High `Stress` and `Fear`. Yukkuris will instinctively seek cover (Behavior Tree update).
    - *Impact*: Yukkuri will get hurt if they stay in the thunderstorm for too long and melt.
- **Snowy**:
    - *Visual*: White screen tint, slow falling snow particles.
    - *Effect*: Snow piles accumulate.
    - *Impact*: Rapid `BodyTemperature` drop.
    - *Impact*: Yukkuri will get hurt if they stay in the snow for too long and freeze.

### Implementation: WeatherService
A dedicated service managing the state machine.
- **Transitions**: Controlled by a weighted Markov Chain defined in `data/weather.toml`, influenced by the current **Season**.
    - *Example*: `Winter` has {Sunny: 0.3, Snow: 0.6, Storm: 0.1}.

## 2. Seasons & Time
A macro-cycle that changes the "rules" of the game every few days.

### The Seasonal Cycle
- **Length**: Configurable, default 1 Season = 7 In-Game Days.
- **Cycle**: Spring -> Summer -> Autumn -> Winter -> Spring.

### Seasonal Effects
1.  **Visuals**:
    - **Spring**: Pink/Pastel tint. Falling petal particles.
    - **Summer**: High saturation, bright lighting. Heat haze effect.
    - **Autumn**: Orange/Sepia tint. Falling leaves.
    - **Winter**: Blue/Cold tint. Desaturated terrain.
    
2.  **Mechanics**:
    - **Spring**: Mating season. Breeding desire +50%.
    - **Summer**: Heat waves. Food spoils 2x faster.
    - **Autumn**: Harvest. Food costs -20%.
    - **Winter**: Freeze. No wild food spawns. Heating cost increases.

## 3. Temperature System (New)
To give Seasons bite, we introduce a thermodynamic simulation.

### The Physics
- **Stats**: Add `BodyTemperature` (Ideal: 37°C [98.6°F]) to `Needs` component.
- **Ambient Temperature**: Controlled by `WeatherService`.
    - Summer Day: 30°C [86°F]
    - Winter Night: -5°C [23°F]
    - Heater Radius: +20°C [68°F] (Attenuated by distance)

### Thermodynamics & Equalization
Temperature is not static; it flows between environments.

- **Zones**: The world is divided into "Outside" and "Inside" zones (defined by walls/roofs).
- **Equalization**:
    - **Open Air**: Fast equalization with Global Ambient Temperature.
    - **Insulation**: Walls/Roofs verify heat transfer.
        - *Concrete/Wood*: High Insulation (Slow change).
        - *Glass/Open Door*: Low Insulation (Fast change).
- **Equation**: `CurrentTemp += (TargetTemp - CurrentTemp) * Conductivity * dt`
    - *Conductivity* ranges from 0.01 (Insulated Wall) to 1.0 (Open Window).
    
### Gameplay Loop
1.  **Exposure**: Yukkuri body temp interpolates towards Ambient Temp.
2.  **Consequences**:
    - **Hyperthermia (>40°C)**: "Heatstroke". Energy drains rapidly. Yukkuri moves slowly.
    - **Hypothermia (<36°C)**: "Shivering". Huge Hunger drain (burning calories to stay warm).
    - **Freezing (<30°C)**: Damage over time. Death.

### Player Mitigation
- Buy **Heaters** (requires electricity) for Winter.
- Buy **Cooling Mats** or **AC Units** for Summer.
- Knit **Scarves/Hats** (Customization item with +Insulation stats).

### Visual Feedback
- **Shivering**: Yukkuri sprite shakes slightly. "Shivers" text bubble.
- **Heatstroke**: Yukkuri sprite turns red/pink. "Panting" animation.
- **Wet**: Yukkuri sprite looks darker/damp.

### Audio Feedback
- **Rain**: Gentle pitter-patter to heavy downpour.
- **Thunder**: Low rumbles to deafening cracks.
- **Wind**: Whistling sounds.
- **Snow**: Muffled ambient noise.

## Technical Architecture

### 1. Components
- **WeatherEffectComponent**: For entities that react to weather (e.g., `Puddle` dries up in Sun, freezes in Snow).
- **ThermalEmitterComponent**: For objects that change ambient temperature (Radiators, Fire).
- **InsulationComponent**: For clothing items that slow temperature change.

### 2. Integration
- **GameLoop**: `WeatherService.update(dt)` -> `TemperatureSystem.update(dt)`.
- **Renderer**:
    - `WeatherRenderer`: Integrated into the main render pipeline `draw_weather(screen, depth)`.
    - `SeasonalRenderer`: A post-process filter (multiply blend mode) applied to the world surface.

### 3. Data Driven
- `data/weather.toml`: Defines transition probabilities per season.
- `data/seasons.toml`: Defines ambient temperature curves for day/night per season.

### 4. UI/UX: Unit Conversion
While the game simulation runs strictly in **Celsius** (C), players can choose their preferred display unit.

- **Option**: `Temperature Display: Celsius | Fahrenheit` in Settings.
- **Conversion**:
    - Internal: All `BodyTemperature` and `AmbientTemp` calculations use Celsius.
    - Display: UI components apply `(C * 9/5) + 32` if Fahrenheit is selected.
    - Input: Heaters/AC settings in the UI will display the chosen unit but set the internal target in Celsius.
