import { createContext, useContext } from "react";
export const WorkspaceContext = createContext(null);
export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Workspace provider missing");
  return value;
}
