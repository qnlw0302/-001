export const state = {
  user: null,
  products: [],
  selectedProduct: null,
  page: 1,
  limit: 10,
  totalPages: 1,
  pendingDelete: null,
  pendingMovement: null,
  defaultThreshold: 5,
  customFieldRows: []
};

let nextCustomRowId = 0;

export function nextRowId() {
  return nextCustomRowId++;
}
