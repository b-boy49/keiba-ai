import type { SVGProps } from "react";

// 線画アイコン（24px グリッド・stroke 1.7）で統一する
const paths = {
  home: <><path d="M3 11.5 12 4l9 7.5" /><path d="M5.5 10v10h13V10" /><path d="M10 20v-5.5h4V20" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15.5" rx="2" /><path d="M3.5 10h17M8 3v4M16 3v4" /><path d="M7.5 13.5h1M11.5 13.5h1M15.5 13.5h1M7.5 17h1M11.5 17h1" /></>,
  brain: <><path d="M12 5.5a3 3 0 0 0-5.6-1A3 3 0 0 0 4 9a3.2 3.2 0 0 0 .5 5.6A3 3 0 0 0 7.5 19a2.6 2.6 0 0 0 4.5 1z" /><path d="M12 5.5a3 3 0 0 1 5.6-1A3 3 0 0 1 20 9a3.2 3.2 0 0 1-.5 5.6 3 3 0 0 1-3 4.4 2.6 2.6 0 0 1-4.5 1" /><path d="M12 5.5V20M8 9.5c1.3 0 2 .7 2 2M16 9.5c-1.3 0-2 .7-2 2M8.5 15h1.5M14 15h1.5" /></>,
  chart: <><path d="M4 4v16h16" /><rect x="7.5" y="11" width="3" height="6" rx=".5" /><rect x="12.5" y="7" width="3" height="10" rx=".5" /><path d="M17.5 4.5 20 7" /></>,
  flag: <><path d="M5.5 21V3.5" /><path d="M5.5 4h12l-2.5 4.25L17.5 12.5h-12" /></>,
  trophy: <><path d="M7.5 4h9v5.5a4.5 4.5 0 0 1-9 0z" /><path d="M7.5 6H4.5a3.5 3.5 0 0 0 3.5 4M16.5 6h3a3.5 3.5 0 0 1-3.5 4" /><path d="M12 14v3.5M8.5 20.5h7M9.5 17.5h5v3h-5z" /></>,
  info: <><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5.5M12 7.6v.4" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m20 20-4.7-4.7" /></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  fire: <path d="M12 3c.6 3 4.5 5.2 4.5 10a4.5 4.5 0 0 1-9 0c0-2.1.9-3.4 2-4.4.1 1.8.8 2.9 1.9 3.4C11 9.6 10.6 6.6 12 3z" />,
  crown: <path d="M3.5 8 8 12l4-6.5 4 6.5 4.5-4-1.8 10.5H5.3z" />,
  megaphone: <><path d="M4 10v4h3l7.5 4.5v-13L7 10z" /><path d="M17.5 9a4 4 0 0 1 0 6M7 14l1.2 5h2.3l-1-4.4" /></>,
  venue: <><rect x="3" y="6.5" width="18" height="11" rx="5.5" /><rect x="7.5" y="10" width="9" height="4" rx="2" /></>,
  list: <path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h1M4.5 12h1M4.5 17.5h1" />,
  arrow: <path d="M4.5 12h15M13.5 6l6 6-6 6" />,
  chevron: <path d="m9 5.5 6.5 6.5L9 18.5" />,
};

export type IconName = keyof typeof paths;

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}>
      {paths[name]}
    </svg>
  );
}

export function HorseMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 64 64" width="1em" height="1em" fill="currentColor" aria-hidden="true" focusable="false" {...props}>
      <path d="M18 60c-3-12 0-22 6-29l-3-10 7 4 3-11 5 10c9 1 17 7 21 16l2 7c0 4-3 6-7 5l-6-3c-3-1-5 0-5 3l3 8z" />
      <path d="M24 26c-5-1-9 2-13 1 3 3 8 3 12 2-4 2-8 6-12 6 4 2 9 0 12-3" opacity=".75" />
      <circle cx="42" cy="31" r="1.8" fill="#04201a" />
    </svg>
  );
}
