/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#F7F5F0',
        surface: {
          DEFAULT: '#FFFFFF',
          secondary: '#F1EEE7',
          tertiary: '#EAE6DD',
        },
        border: {
          DEFAULT: '#E4E0D7',
          darker: '#D5D0C5',
        },
        primary: {
          DEFAULT: '#24231F',
          muted: '#6F6B63',
          faint: '#9A958B',
        },
        accent: {
          DEFAULT: '#536B5D',
          hover: '#45594D',
          light: '#EBF0ED',
          border: '#BCCBC2',
        },
        risk: {
          high: '#B83A3A',
          highBg: '#FDF2F2',
          highBorder: '#F5C6C6',
          warning: '#C07D2B',
          warningBg: '#FEF9F0',
          warningBorder: '#F5DEB8',
          legit: '#3E7A5E',
          legitBg: '#F0F7F3',
          legitBorder: '#C1DFCF',
          approval: '#C46D29',
          approvalBg: '#FFF6EF',
          approvalBorder: '#FCD7BC',
          neutral: '#8C877D',
          neutralBg: '#F5F4F0',
        }
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '8px',
        md: '8px',
        lg: '10px',
        xl: '12px',
      },
      boxShadow: {
        subtle: '0 1px 2px rgba(36, 35, 31, 0.04)',
        card: '0 1px 3px rgba(36, 35, 31, 0.06)',
      }
    },
  },
  plugins: [],
}
