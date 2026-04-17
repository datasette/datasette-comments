export interface State<T, E> {
  isLoading: boolean;
  data?: T;
  error?: E;
}
export type Action<T, E> =
  | { type: "init" }
  | { type: "success"; data: T }
  | { type: "failure"; error: E };

export function apiReducer<
  T,
  E,
  TState extends State<T, E>,
  TAction extends Action<T, E>
>(state: TState, action: TAction): TState {
  switch (action.type) {
    case "init":
      return {
        ...state,
        isLoading: true,
      };
    case "failure":
      return { ...state, isLoading: false, error: action.error };
    case "success":
      return {
        ...state,
        isLoading: false,
        data: action.data,
      };
  }
}
