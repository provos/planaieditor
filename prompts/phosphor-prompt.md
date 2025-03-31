# phosphor-svelte

Phosphor is a flexible icon family for interfaces, diagrams, presentations — whatever, really. More icons at [phosphoricons.com](https://phosphoricons.com).

## Installation

```shell
yarn add --dev phosphor-svelte
```

or

```shell
npm install --save-dev phosphor-svelte
```

## Usage

```svelte
<script>
  import { Horse, Heart } from "phosphor-svelte";
  // or
  import Cube from "phosphor-svelte/lib/Cube"; // Recommended for faster compiling
</script>

<Horse />
<Heart color="#AE2983" weight="fill" size="{32}" />
<Cube color="teal" weight="duotone" />
```

> **Warning**
> You might encounter slower compilation when importing components using named import (`import { X } from "phosphor-svelte"`).

### Props

- **color?**: `string` – Icon stroke/fill color. Can be any CSS color string, including `hex`, `rgb`, `rgba`, `hsl`, `hsla`, named colors, or the special `currentColor` variable.
- **size?**: `number | string` – Icon height & width. As with standard React elements, this can be a number, or a string with units in `px`, `%`, `em`, `rem`, `pt`, `cm`, `mm`, `in`.
- **weight?**: `"thin" | "light" | "regular" | "bold" | "fill" | "duotone"` – Icon weight/style. Can also be used, for example, to "toggle" an icon's state: a rating component could use Stars with `weight="regular"` to denote an empty star, and `weight="fill"` to denote a filled star.
- **mirrored?**: `boolean` – Flip the icon horizontally. Can be useful in RTL languages where normal icon orientation is not appropriate.

### Context

Apply default style to all icons. Create an IconContext at the root of the app (or anywhere above the icons in the tree) and pass in a configuration object with props to be applied by default to all icons inside context:

```svelte
<script>
  import IconContext from "phosphor-svelte/lib/IconContext";
  // or
  // import { IconContext } from "phosphor-svelte";

  import Cube from "phosphor-svelte/lib/Cube";
  import Horse from "phosphor-svelte/lib/Horse";
  import Heart from "phosphor-svelte/lib/Heart";
</script>

<IconContext
  values={{ color: 'limegreen', size: 32, mirrored: false, weight: 'bold' }}>
  <Horse /> <Heart /> <Cube color="red" /> </IconContext>
```

### Composability

<p align="right"><img src="/haruaki07/phosphor-svelte/raw/main/meta/cube-rotate.svg" width="128"></p>

Components can accept arbitrary SVG elements as children, so long as they are valid children of the `<svg>` element. This can be used to modify an icon with background layers or shapes, filters, animations and more. The children will be placed *below* the normal icon contents.

The following will cause the Cube icon to rotate and pulse:

```svelte
<Cube color="darkorchid" weight="duotone">
  <animate
    attributeName="opacity"
    values="0;1;0"
    dur="4s"
    repeatCount="indefinite"
  ></animate>
  <animateTransform
    attributeName="transform"
    attributeType="XML"
    type="rotate"
    dur="5s"
    from="0 0 0"
    to="360 0 0"
    repeatCount="indefinite"
  ></animateTransform>
</Cube>
```

> **Note:** The coordinate space of slotted elements is relative to the contents of the icon `viewBox`, which is a 256x256 square. Only [valid SVG elements](https://developer.mozilla.org/en-US/docs/Web/SVG/Element#SVG_elements_by_category) will be rendered.

### Import Optimizer

A Vite plugin that transforms named import to default import. This will speed up compile times during development.

```diff
<script>
-  import { Cube, Heart, Horse } from "phosphor-svelte";
+  import Cube from "phosphor-svelte/lib/Cube";
+  import Heart from "phosphor-svelte/lib/Heart";
+  import Horse from "phosphor-svelte/lib/Horse";
</script>
```
#### Usage
Add the plugin into your vite config file.

```js
// vite.config.ts

import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";
import { sveltePhosphorOptimize } from "phosphor-svelte/vite";

export default defineConfig({
  plugins: [sveltePhosphorOptimize(), sveltekit()],
});
```

## License

MIT © [Phosphor Icons](https://github.com/phosphor-icons)