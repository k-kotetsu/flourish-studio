/**
 * 4領域(Career/Financial/Physical/Social)の線画アイコン(P7-3、`07_デザイン原則`7.6)。
 * 「4領域のアイコンは既製セットから選んでよい」に基づき、`docs/06_ワイヤーフレーム/mockup.html`の
 * `ICON`(Career/Financial/Physical/Social)をそのまま採用した。24pxグリッド、線幅1.6px、
 * 線端・接合部を丸める、塗りつぶしなし、`currentColor`で継承(2.6「4領域の色分けはしない」ため
 * 領域固有の色は持たせない)という要件にmockup.html時点ですでに合致している。
 * 表示は`AreaIcon.vue`が担う。
 */
import { CAREER, FINANCIAL, PHYSICAL, SOCIAL, type Area } from "./questions";

export type AreaIconElement =
  | { readonly tag: "path"; readonly d: string }
  | { readonly tag: "circle"; readonly cx: number; readonly cy: number; readonly r: number }
  | {
      readonly tag: "rect";
      readonly x: number;
      readonly y: number;
      readonly width: number;
      readonly height: number;
      readonly rx: number;
    };

export interface AreaIconShape {
  readonly viewBox: string;
  readonly elements: readonly AreaIconElement[];
}

export const AREA_ICONS: Readonly<Record<Area, AreaIconShape>> = {
  [CAREER]: {
    viewBox: "0 0 24 24",
    elements: [
      { tag: "rect", x: 3, y: 7, width: 18, height: 13, rx: 2 },
      { tag: "path", d: "M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" },
      { tag: "path", d: "M3 12h18" },
    ],
  },
  [FINANCIAL]: {
    viewBox: "0 0 24 24",
    elements: [
      { tag: "circle", cx: 12, cy: 12, r: 8 },
      {
        tag: "path",
        d: "M12 7v10M9.5 9.8c0-1 1.1-1.8 2.5-1.8s2.5.8 2.5 1.8-1.1 1.8-2.5 1.8-2.5.8-2.5 1.8 1.1 1.8 2.5 1.8 2.5-.8 2.5-1.8",
      },
    ],
  },
  [PHYSICAL]: {
    viewBox: "0 0 24 24",
    elements: [
      { tag: "path", d: "M12 20s-7-4.3-7-9a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 4.7-7 9-7 9z" },
      { tag: "path", d: "M3 12h3l1.5-2.5L9.5 14 11 12h2" },
    ],
  },
  [SOCIAL]: {
    viewBox: "0 0 24 24",
    elements: [
      { tag: "circle", cx: 9, cy: 8, r: 3 },
      { tag: "path", d: "M3 20c0-3.3 2.7-5 6-5s6 1.7 6 5" },
      { tag: "circle", cx: 17.5, cy: 9.5, r: 2.5 },
      { tag: "path", d: "M16 15c3 0 5 1.6 5 4.5" },
    ],
  },
};
