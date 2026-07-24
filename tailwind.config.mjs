/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        // Paleta litúrgica (ver web.md sección 3.2)
        brand: {
          50: '#FAF6F0',
          100: '#F2E8DA',
          200: '#E4D0B0',
          300: '#D4A574',
          400: '#B8874D',
          500: '#8B6432',
          600: '#6B4423',
          700: '#553620',
          800: '#3F2818',
          900: '#2C1810',
        },
        accent: {
          DEFAULT: '#8B0000',
          light: '#B22222',
          dark: '#5C0000',
        },
        cream: '#FAF6F0',
        sepia: '#2C1810',
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};