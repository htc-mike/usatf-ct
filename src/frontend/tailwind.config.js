/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Barlow Condensed"', 'sans-serif'],
        sans: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        brand: {
          navy:    '#00234B',
          blue:    '#0057B8',
          gold:    '#F59E0B',
          red:     '#CC0000',
          light:   '#F0F4F9',
          muted:   '#64748B',
        },
      },
    },
  },
  plugins: [],
}
