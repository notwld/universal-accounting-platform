export type ApiData<T> = {
  data: T;
  meta?: Record<string, unknown>;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    field_errors?: Record<string, string[]>;
    request_id?: string;
    timestamp?: string;
  };
};
