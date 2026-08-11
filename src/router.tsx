import { createRouter } from "@tanstack/react-router";
import { createQueryClient } from "./lib/queryClient";
import { routeTree } from "./routeTree.gen";

export const getRouter = () => {
  const queryClient = createQueryClient();

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};
