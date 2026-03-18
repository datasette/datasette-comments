import createClient from "openapi-fetch";
import type { paths } from "../generated/api";

export const client = createClient<paths>({ baseUrl: "" });
