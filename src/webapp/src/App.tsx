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
	return (
		<FluentProvider theme={webLightTheme}>
			<BrowserRouter>
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
							padding: "96px",
							paddingBottom: "64px",
							overflow: "auto",
							height: "100vh",
						}}
					>
						<Routes>
							<Route path="/" element={<Navigate to="/agents" replace />} />
							<Route path="/datasets" element={<DatasetsPage />} />
							<Route path="/datasets/:id" element={<DatasetDetailPage />} />
							<Route path="/datasets/:id/testcases/:testcase_id" element={<TestCaseDetailPage />} />
							<Route path="/agents" element={<AgentsPage />} />
							<Route path="/agents/:id" element={<AgentDetailPage />} />
							<Route path="/evaluations/:id" element={<EvaluationResultsPage />} />
							<Route path="/evaluations/:eval_id/testcases/:testcase_id" element={<TestCaseResultPage />} />
							<Route path="/leaderboard" element={<LeaderboardPage />} />
						</Routes>
					</main>
					<Toaster />
				</div>
			</BrowserRouter>
		</FluentProvider>
	);
}

export default App;
