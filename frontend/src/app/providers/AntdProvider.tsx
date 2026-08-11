import {
  App as AntdApp,
  theme as antdTheme,
  ConfigProvider,
  type ThemeConfig,
} from "antd"

import { useTheme } from "@/shared/components/theme/ThemeProvider"

const { darkAlgorithm, defaultAlgorithm } = antdTheme

const baseTheme: ThemeConfig = {
  cssVar: {
    key: "fastapi-template",
  },
  token: {
    borderRadius: 8,
    colorPrimary: "#0f766e",
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
}

export function AntdProvider({ children }: { children: React.ReactNode }) {
  const { resolvedTheme } = useTheme()

  return (
    <ConfigProvider
      theme={{
        ...baseTheme,
        algorithm: resolvedTheme === "dark" ? darkAlgorithm : defaultAlgorithm,
      }}
    >
      <AntdApp>{children}</AntdApp>
    </ConfigProvider>
  )
}
