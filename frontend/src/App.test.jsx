import { afterEach, expect, test, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import App from "./App";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test("clears data from the previous tenant before the next workspace finishes loading", async () => {
  let workspace = "A";
  let hold = false;
  let release;
  const user = () => ({
    email: "admin@example.test",
    role: "admin",
    tenant_id: workspace,
    tenant_name: "Workspace " + workspace,
    ai_mode: "demo",
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, options = {}) => {
      const response = (data) => ({
        ok: true,
        status: 200,
        json: async () => data,
      });
      if (url === "/api/auth/logout") return { status: 204, ok: true };
      if (url === "/api/auth/login") {
        workspace = "B";
        hold = true;
        return response({});
      }
      if (url === "/api/me") return response(user());
      if (url === "/api/customers") {
        if (hold)
          return await new Promise((resolve) => {
            release = () =>
              resolve(
                response([
                  {
                    id: "b",
                    name: "Beta Customer",
                    risk: "low",
                    plan: "Enterprise",
                    usage_change: 0,
                    open_tickets: 0,
                    mrr: 100,
                  },
                ]),
              );
          });
        return response([
          {
            id: "a",
            name: "Private Alpha Customer",
            risk: "low",
            plan: "Enterprise",
            usage_change: 0,
            open_tickets: 0,
            mrr: 100,
          },
        ]);
      }
      return response(url === "/api/metrics" ? {} : []);
    }),
  );
  render(<App />);
  await screen.findByText("Private Alpha Customer");
  fireEvent.click(
    screen.getByRole("button", { name: "Sign out", exact: true }),
  );
  await screen.findByLabelText("Password");
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "test-password-123" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in to workspace" }));
  await screen.findByText("Workspace B");
  expect(screen.queryByText("Private Alpha Customer")).not.toBeInTheDocument();
  await waitFor(() => expect(release).toBeTypeOf("function"));
  release();
  await screen.findByText("Beta Customer");
  expect(screen.queryByText("Private Alpha Customer")).not.toBeInTheDocument();
});
