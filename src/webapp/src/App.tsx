import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DatasetsPage } from "./components/datasets/DatasetsPage";
import { DatasetDetailPage } from "./components/datasets/DatasetDetailPage";
import { TestCaseDetailPage } from "./components/datasets/TestCaseDetailPage";
import { AgentsPage } from "./components/agents/AgentsPage";
import { AgentDetailPage } from "./components/agents/AgentDetailPage";
import { EvaluationResultsPage } from "./components/results/EvaluationResultsPage";
import { TestCaseResultPage } from "./components/results/TestCaseResultPage";
import { LeaderboardPage } from "./components/leaderboard/LeaderboardPage";
import { Navigation } from "./components/layout/Navigation";
import { Toaster } from "@/components/ui/sonner";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";

function App() {

  const [isInitialized, setIsInitialized] = useState(!isAuthEnabled); // Skip initialization if auth disabled

  useEffect(() => {
    if (!isAuthEnabled) {
      // Auth is disabled, proceed without MSAL initialization
      return;
    }

    const initializeMsal = async () => {
      if (!msalInstance) return;

      try {
        await msalInstance.initialize();
        const response = await msalInstance.handleRedirectPromise();

        if (
          !response &&
          msalInstance.getAllAccounts().length === 0 &&
          !hasTriggeredLogin
        ) {
          hasTriggeredLogin = true;
          await msalInstance.loginRedirect({
            scopes: ["User.Read"],
          });
          return;
        }

        setIsInitialized(true);
      } catch (error) {
        console.error("Error initializing MSAL or handling redirect:", error);
        setIsInitialized(true);
      }
    };

    initializeMsal();
  }, []);

  if (!isInitialized) {
    return null;
  }

  // Conditionally wrap with MsalProvider only if auth is enabled
  const content = (
    <AuthProvider>
      <FluentProvider theme={webLightTheme}>
        <BrowserRouter>
          <AuthenticatedRoute>
            <div
              className="bg-background"
              style={{
                height: "100vh",
                width: "100vw",
                display: "flex",
                overflow: "hidden",
              }}
            >
              <Navigation />
              <main
                className="flex-1"
                style={{
                  padding: "48px",
                  paddingTop: "32px",
                  paddingBottom: "32px",
                  overflow: "auto",
                  height: "100vh",
                  minWidth: 0,
                }}
              >
                <Routes>
                  <Route path="/" element={<Navigate to="/agents" replace />} />
                  <Route path="/datasets" element={<DatasetsPage />} />
                  <Route path="/datasets/create" element={<CreateDatasetPage />} />
                  <Route path="/datasets/:id" element={<DatasetDetailPage />} />
                  <Route
                    path="/datasets/:id/testcases/:testcase_id"
                    element={<TestCaseDetailPage />}
                  />
                  <Route path="/agents" element={<AgentsPage />} />
                  <Route path="/agents/:id" element={<AgentDetailPage />} />
                  <Route
                    path="/evaluations/:id"
                    element={<EvaluationResultsPage />}
                  />
                  <Route
                    path="/evaluations/:eval_id/testcases/:testcase_id"
                    element={<TestCaseResultPage />}
                  />
                  <Route path="/leaderboard" element={<LeaderboardPage />} />
                  {/* Legacy routes for backward compatibility */}
                  <Route
                    path="/scenarios"
                    element={<Navigate to="/datasets" replace />}
                  />
                  <Route
                    path="/scenarios/:id"
                    element={<Navigate to="/datasets/:id" replace />}
                  />
                </Routes>
              </main>
              <Toaster />
            </div>
          </AuthenticatedRoute>
        </BrowserRouter>
      </FluentProvider>
    </AuthProvider>
  );

  return isAuthEnabled && msalInstance ? (
    <MsalProvider instance={msalInstance}>{content}</MsalProvider>
  ) : (
    content
  );
}

export default App;
