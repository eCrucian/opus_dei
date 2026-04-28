/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 700: '#1a3a5c', 800: '#12294a', 900: '#0c1e36' },
        brand: { 500: '#2563eb', 600: '#1d4ed8' },
      },
    },
  },
  plugins: [],
}
