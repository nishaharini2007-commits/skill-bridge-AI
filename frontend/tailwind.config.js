/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { ink: '#172b4d', muted: '#667085', accent: '#4d6bfa', teal: '#12a98b' }, boxShadow: { soft: '0 12px 32px rgba(28, 43, 81, .07)' } } },
  plugins: [],
}
