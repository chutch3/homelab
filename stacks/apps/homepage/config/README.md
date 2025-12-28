# Homepage Configuration

This directory contains all configuration files for the Homepage dashboard.

## Files

- **settings.yaml** - Main homepage settings (theme, layout, title, etc.)
- **widgets.yaml** - Top bar widgets (weather, resources, search, etc.)
- **bookmarks.yaml** - Quick access bookmark links
- **services.yaml** - Manual service definitions (currently using auto-discovery)
- **docker.yaml** - Docker integration configuration for service discovery
- **custom.css** - Custom CSS styling
- **custom.js** - Custom JavaScript (currently unused)

## Customization

### Change Weather Location
Edit `widgets.yaml` and update the coordinates:
```yaml
- openmeteo:
    latitude: YOUR_LATITUDE
    longitude: YOUR_LONGITUDE
```

### Change Theme Color
Edit `settings.yaml` and change the `color` value to one of:
- red, orange, amber, yellow, lime, green, emerald, teal, cyan, sky, blue, indigo, violet, purple, fuchsia, pink, rose, slate, gray, zinc, neutral, stone

### Add Bookmarks
Edit `bookmarks.yaml` and add your links following the existing format.

### Modify CSS Styling
Edit `custom.css` to customize colors, animations, and styling.

## Deployment

After making changes, redeploy the homepage stack:
```bash
./homelab deploy --skip-infra --only-apps homepage
```

Or directly:
```bash
docker stack deploy -c stacks/apps/homepage/docker-compose.yml homepage
```
