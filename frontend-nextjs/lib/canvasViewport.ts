export interface CanvasViewTransform {
  x: number;
  y: number;
  zoom: number;
}

export interface CanvasZoomOptions {
  minZoom?: number;
  maxZoom?: number;
  wheelSensitivity?: number;
}

const DEFAULT_MIN_ZOOM = 0.3;
const DEFAULT_MAX_ZOOM = 4;
const DEFAULT_WHEEL_SENSITIVITY = 0.0012;

export function clampCanvasZoom(
  zoom: number,
  minZoom = DEFAULT_MIN_ZOOM,
  maxZoom = DEFAULT_MAX_ZOOM
) {
  return Math.min(maxZoom, Math.max(minZoom, zoom));
}

export function getWheelZoomFactor(deltaY: number, sensitivity = DEFAULT_WHEEL_SENSITIVITY) {
  return Math.exp(-deltaY * sensitivity);
}

export function zoomCanvasViewAt(
  view: CanvasViewTransform,
  viewportRect: Pick<DOMRect, 'left' | 'top'>,
  clientX: number,
  clientY: number,
  factor: number,
  options: CanvasZoomOptions = {}
): CanvasViewTransform {
  const minZoom = options.minZoom ?? DEFAULT_MIN_ZOOM;
  const maxZoom = options.maxZoom ?? DEFAULT_MAX_ZOOM;
  const nextZoom = clampCanvasZoom(view.zoom * factor, minZoom, maxZoom);
  const pointerX = clientX - viewportRect.left;
  const pointerY = clientY - viewportRect.top;
  const worldX = (pointerX - view.x) / view.zoom;
  const worldY = (pointerY - view.y) / view.zoom;

  return {
    x: pointerX - worldX * nextZoom,
    y: pointerY - worldY * nextZoom,
    zoom: nextZoom,
  };
}

export function screenPointToCanvasPoint(
  view: CanvasViewTransform,
  viewportRect: Pick<DOMRect, 'left' | 'top'>,
  clientX: number,
  clientY: number
) {
  return {
    x: (clientX - viewportRect.left - view.x) / view.zoom,
    y: (clientY - viewportRect.top - view.y) / view.zoom,
  };
}
