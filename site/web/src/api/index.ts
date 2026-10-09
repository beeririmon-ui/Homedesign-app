import type { StoreApi } from './types';
import { httpApi } from './http';
import { mockApi } from './mock';

export const api: StoreApi = __ARTIFACT__ ? mockApi : httpApi;
export { ApiError } from './types';
