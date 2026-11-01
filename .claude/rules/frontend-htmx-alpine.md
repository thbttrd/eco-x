---
paths: ecox-client/templates/**/*.html, ecox-client/static/**/*.js
---

# Frontend: HTMX + Alpine.js Integration

## Critical: Alpine Components in HTMX-Loaded Content

**Problem**: When HTMX loads content via `innerHTML` swap, `<script>` tags inside the loaded content **do not execute**. This means Alpine.js components defined inline in partials won't be registered.

**Symptom**: Console errors like `Alpine Expression Error: <componentName> is not defined`

### WRONG - Inline script in HTMX-loaded partial

```html
<!-- partials/_my_partial.html - BROKEN when loaded via HTMX -->
<div x-data="myComponent()">
    <!-- content -->
</div>

<script>
    function myComponent() {
        return {
            // This script NEVER executes when loaded via HTMX!
        }
    }
</script>
```

### CORRECT - Global registration in base.html

```html
<!-- base.html - Register BEFORE Alpine.js loads -->
<script>
    document.addEventListener('alpine:init', () => {
        Alpine.data('myComponent', () => ({
            // Component definition here

            init() {
                // Read initial state from data attributes
                const el = this.$el;
                if (el.dataset.someValue) {
                    this.someValue = el.dataset.someValue;
                }
            }
        }));
    });
</script>

<!-- Alpine.js CDN comes AFTER the registration -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

```html
<!-- partials/_my_partial.html - Use data attributes for initial state -->
<div x-data="myComponent"
     data-some-value="{{ some_value }}"
     data-items="{{ items|tojson }}">
    <!-- content -->
</div>
```

### HTMX After-Swap Reinitialization

Add this to `base.html` to reinitialize Alpine on dynamically loaded content:

```javascript
document.addEventListener('htmx:afterSwap', (event) => {
    const target = event.detail.target;
    if (target && window.Alpine) {
        Alpine.initTree(target);
    }
});
```

## Summary

| Aspect | Wrong | Correct |
|--------|-------|---------|
| Component definition | Inline `<script>` in partial | `Alpine.data()` in base.html |
| Initial state | Inline Jinja in JS | Data attributes + `init()` |
| x-data syntax | `x-data="component()"` | `x-data="component"` |
| Dynamic content | Not handled | `htmx:afterSwap` handler |
