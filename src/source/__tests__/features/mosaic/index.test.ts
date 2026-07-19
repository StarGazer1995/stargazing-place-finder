import { describe, it, expect } from 'vitest';
import { renderMosaicPanel } from '../../../js/features/mosaic/index';
import type { MosaicGrid } from '../../../js/types/telescope';

function makeGrid(rows: number, cols: number): MosaicGrid {
  const panels = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      panels.push({
        row: r, col: c,
        ra_center: 10 + r * 2 + c * 0.5,
        dec_center: 40 + r * 1,
        corners: [[10, 40], [11, 40], [11, 41], [10, 41]] as [number, number][],
      });
    }
  }
  return {
    rows, cols,
    total_panels: rows * cols,
    overlap: 0.15,
    fov_width_deg: 1.5,
    fov_height_deg: 1.0,
    panels,
  };
}

describe('renderMosaicPanel', () => {
  it('renders the grid summary line', () => {
    const container = document.createElement('div');
    const grid = makeGrid(3, 4);
    renderMosaicPanel(grid, container);

    expect(container.innerHTML).toContain('3×4');
    expect(container.innerHTML).toContain('12 面板');
    expect(container.innerHTML).toContain('15%');
    expect(container.innerHTML).toContain('1.50°×1.00°');
  });

  it('renders all panel entries', () => {
    const container = document.createElement('div');
    const grid = makeGrid(2, 2);
    renderMosaicPanel(grid, container);

    // Should have entries for [0,0], [0,1], [1,0], [1,1]
    expect(container.innerHTML).toContain('[0,0]');
    expect(container.innerHTML).toContain('[0,1]');
    expect(container.innerHTML).toContain('[1,0]');
    expect(container.innerHTML).toContain('[1,1]');
  });

  it('displays RA/Dec for each panel', () => {
    const container = document.createElement('div');
    const grid = makeGrid(1, 1);
    renderMosaicPanel(grid, container);

    expect(container.innerHTML).toContain('RA');
    expect(container.innerHTML).toContain('Dec');
  });

  it('includes the overlap hint text', () => {
    const container = document.createElement('div');
    const grid = makeGrid(2, 2);
    renderMosaicPanel(grid, container);

    expect(container.innerHTML).toContain('蓝色虚线框');
    expect(container.innerHTML).toContain('重叠率滑块');
  });

  it('renders correctly for a single-panel grid', () => {
    const container = document.createElement('div');
    const grid = makeGrid(1, 1);
    renderMosaicPanel(grid, container);

    expect(container.innerHTML).toContain('1×1');
    expect(container.innerHTML).toContain('1 面板');
  });
});
