import { createTheme, type MantineColorsTuple } from '@mantine/core';

/** The sheet's ink blue, and darker reds and greens than Mantine's: every shade used for text or
 * as a filled button reads at 4.5:1 or better on the paper background. */
const ink: MantineColorsTuple = ['#eef3f6', '#dde7ec', '#b9ccd6', '#92afbe', '#7097aa', '#527f96', '#366880', '#254c62', '#1d3d4f', '#162e3c'];
const red: MantineColorsTuple = ['#fbeeee', '#f5dcdc', '#e8b4b4', '#da8a8a', '#cd6565', '#c04a4a', '#a12c2c', '#8a2424', '#731d1d', '#5c1717'];
const green: MantineColorsTuple = ['#ecf5ef', '#d9eadf', '#b0d3bc', '#84ba97', '#5fa578', '#469563', '#2f7a4b', '#256440', '#1c4f32', '#143a25'];
const yellow: MantineColorsTuple = ['#fbf4e6', '#f6ead6', '#ecd3a8', '#e1bb77', '#d8a64e', '#c98f2f', '#a8721f', '#805315', '#664211', '#4d320d'];

const sans = '"IBM Plex Sans", "Helvetica Neue", sans-serif';
const mono = '"IBM Plex Mono", ui-monospace, monospace';
/** Controls are 44px tall (styles.css), the smallest comfortable touch target. */
const control = { defaultProps: { size: 'md' } };

export const theme = createTheme({
  primaryColor: 'ink', primaryShade: 7, colors: { ink, red, green, yellow },
  defaultRadius: 'xs', fontFamily: sans, fontFamilyMonospace: mono, headings: { fontFamily: sans, fontWeight: '600' },
  components: {
    Button: control, TextInput: control, NativeSelect: control, MultiSelect: control, Autocomplete: control,
    Textarea: control, Checkbox: control, Switch: control, SegmentedControl: control,
    ActionIcon: { defaultProps: { size: 44 } },
    Badge: { defaultProps: { radius: 'xs', tt: 'none' } },
  },
});
