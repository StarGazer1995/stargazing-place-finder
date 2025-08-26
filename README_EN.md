# Stargazing Place Finder

English | [中文](README.md)

## Project Introduction

This is an application designed specifically for Chinese stargazing enthusiasts, aimed at helping users find suitable stargazing locations while avoiding popular tourist spots, providing a purer stargazing experience.

## Features

- 🌌 **Intelligent Location Recommendations**: Recommend the most suitable stargazing locations based on light pollution data and geographic information
- 🗺️ **Avoid Popular Spots**: Intelligently filter out popular tourist destinations to find quieter stargazing venues
- 📊 **Data Visualization**: Use heat maps to display light pollution conditions in surrounding areas
- 🏔️ **Elevation Filtering**: Prioritize locations with higher elevation and open views

## Technical Architecture

### Data Sources

1. **Chinese Map Data**: Provides basic geographic information and administrative divisions
2. **NASA Dark Sky Map**: Uses NASA-provided light pollution data to obtain accurate dark sky information

### Core Algorithm Workflow

#### 1. Location Filtering
- Use dark sky maps to detect light pollution levels at locations
- Filter out areas with darkness levels suitable for stargazing

#### 2. Map Visualization
1. **Elevation Filtering**: Search for locations with elevation 100+ meters higher than surrounding areas (10km search radius)
2. **Darkness Detection**: Obtain light pollution values for the location from dark sky maps
3. **Surrounding Analysis**: Analyze light pollution conditions in surrounding areas to build heat maps
4. **Map Display**: Use OpenStreetMap for visualization

## Technology Stack

- **Map Service**: OpenStreetMap
- **Data Source**: NASA Light Pollution Map
- **Visualization**: Heat map display
- **Geographic Data**: Chinese map data

## Legal Notice

⚠️ **Important Reminder**: This application strictly complies with relevant Chinese laws and regulations when using elevation data for location filtering. Please pay attention to relevant legal requirements during use.

## Use Cases

- Astrophotography enthusiasts looking for shooting locations
- Stargazing event organizers selecting venues
- Astronomical education activity venue selection
- Personal stargazing experience optimization

## Project Status

✅ **Feature Complete** - Core project features have been developed and tested, including:
- ✅ Mountain peak finding and filtering functionality
- ✅ Light pollution data analysis functionality
- ✅ Road connectivity detection functionality
- ✅ Comprehensive scoring and ranking system
- ✅ Complete test coverage
- ✅ Detailed usage documentation

🔄 **Continuous Optimization** - Welcome code contributions and suggestions for further project improvement.

## 📋 Todo List

### 🎯 Core Features
- [x] Light pollution mandatory detection: Ensure dark sky quality of stargazing locations
- [x] Road accessibility analysis: Balance stargazing quality with transportation convenience

### 🚀 Feature Enhancements
- [ ] **Avoid Popular Spots**: Intelligently filter quiet stargazing locations away from popular tourist spots and crowded areas
- [ ] Scientific scoring system: Intelligent scoring algorithm based on multi-dimensional data
- [ ] Add weather data integration, provide real-time weather forecasts
- [ ] Support user-customizable scoring weights
- [ ] Add lunar phase information and optimal observation time recommendations
- [ ] Develop mobile applications
- [ ] Add user rating and sharing features

### 🌐 Data Expansion
- [ ] Support more light pollution data sources
- [ ] Integrate satellite cloud imagery data
- [ ] Add international dark sky preserve data
- [ ] Support global location analysis

## Contributing Guidelines

Welcome developers interested in this project to contribute! Please ensure your code meets the project's coding standards and is thoroughly tested before submission.

## License

This project uses an open source license. Please refer to the LICENSE file for specific license information.

---

*Let's explore the starry sky together and find the most beautiful stargazing locations!* ✨