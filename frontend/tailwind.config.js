/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Olive green brand scale
        olive: {
          50: '#f7f8ee',
          100: '#edf0da',
          200: '#dbe2ba',
          300: '#c2cd90',
          400: '#a8b76a',
          500: '#8b9c4d',
          600: '#6f813b',
          700: '#5f7331',
          800: '#566728',
          900: '#4e5c24',
          950: '#2f3919',
        },
        // Lavender brand scale
        lavender: {
          50: '#f6f4fb',
          100: '#eeeafb',
          200: '#ddd8f6',
          300: '#c5bcee',
          400: '#a99ae4',
          500: '#8d7ad6',
          600: '#745fc0',
          700: '#5f4ca3',
          800: '#4d3e85',
          900: '#3f3269',
          950: '#241c3d',
        },
        // Legacy token names preserved; values now map to the olive/lavender brand.
        navy: '#3a451c',           // darkest olive ink: headings/body text
        'deep-blue': '#4e5c24',    // olive-900: gradients, deep accents
        primary: '#6f813b',        // olive-600: links, icons, primary accents
        purple: '#745fc0',         // lavender-600: secondary accent
        pink: '#a48ae0',           // lavender-400: former pink accents become lavender
        'light-purple': '#eeeafb', // lavender-100
        'light-blue': '#f7f8ee',   // olive-50: app background
      },
      boxShadow: {
        card: '0 10px 30px rgba(63, 74, 32, 0.10)',
      },
    },
  },
  plugins: [],
}
