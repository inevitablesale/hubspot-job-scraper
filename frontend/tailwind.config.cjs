/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: '#0f1115',
        panel: '#11141a',
        accent: '#34d399',
        warn: '#facc15',
        danger: '#f87171',
      },
      boxShadow: {
        soft: '0 10px 40px rgba(0,0,0,0.35)',
      },
    },
  },
  plugins: [],
}
