import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  CircleNotch,
  Clock,
} from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbDivider,
  BreadcrumbButton,
  makeStyles,
  Tooltip,
  isTruncatableBreadcrumbContent,
  truncateBreadcrumbLongName,
} from "@fluentui/react-components";
import { Document20Regular } from "@fluentui/react-icons";
import { AIContentDisclaimer } from "@/components/shared/AIContentDisclaimer";
import { useEvaluation } from "@/hooks/useEvaluation";
import { useSelectableClick } from "@/hooks/useSelectableClick";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { useAgents } from "@/hooks/useAgents";
import { useDatasets } from "@/hooks/useDatasets";

const useBreadcrumbStyles = makeStyles({
  // Remove custom styles since we're using Fluent UI's built-in truncation
});

export function EvaluationResultsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const breadcrumbStyles = useBreadcrumbStyles();
  const { evaluation, testCases, loading, error } = useEvaluation(id, true); // Enable polling
  const { agents } = useAgents();
  const { datasets } = useDatasets();
  const { createClickHandler } = useSelectableClick();

  // Get agent and dataset details
  const agent = evaluation
    ? agents.find((a) => a.id === evaluation.agent_id)
    : null;
  const dataset = evaluation
    ? datasets.find((s) => s.id === evaluation.dataset_id)
    : null;
  const agentName = agent?.name;
  const evaluationName = evaluation?.name;

  // Helper function to get test case name
  const getTestCaseName = (testcaseId: string) => {
    const testCase = testCases.find((tc) => tc.id === testcaseId);
    return testCase?.name || `Test Case ${testcaseId}`;
  };

  const handleTestCaseClick = createClickHandler((testcaseId: string) => {
    navigate(`/evaluations/${id}/testcases/${testcaseId}`);
  });

  const progressPercentage =
    evaluation && evaluation.total_tests > 0
      ? (evaluation.completed_tests / evaluation.total_tests) * 100
      : 0;
  // Pass rate should be out of total tests, not just completed tests
  const passRate =
    evaluation && evaluation.total_tests > 0
      ? Math.round(
          (evaluation.passed_count / evaluation.total_tests) * 100
        ).toString()
      : "N/A";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <CircleNotch size={48} className="animate-spin text-primary mb-4" />
        <p className="text-muted-foreground">Loading evaluation...</p>
      </div>
    );
  }

  if (error || !evaluation) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h2 className="text-2xl font-bold mb-2">Evaluation not found</h2>
        <p className="text-muted-foreground mb-6">
          {error || "The evaluation you're looking for doesn't exist."}
        </p>
        <Button
          onClick={() => navigate("/agents")}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft size={18} />
          Back to Agents
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Compact header section */}
      <div className="space-y-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <Breadcrumb aria-label="Agent navigation" className="mb-4">
              <BreadcrumbItem>
                {isTruncatableBreadcrumbContent("Agents", 30) ? (
                  <Tooltip withArrow content="Agents" relationship="label">
                    <BreadcrumbButton onClick={() => navigate("/agents")}>
                      {truncateBreadcrumbLongName("Agents")}
                    </BreadcrumbButton>
                  </Tooltip>
                ) : (
                  <BreadcrumbButton onClick={() => navigate("/agents")}>
                    Agents
                  </BreadcrumbButton>
                )}
              </BreadcrumbItem>
              <BreadcrumbDivider />
              <BreadcrumbItem>
                {isTruncatableBreadcrumbContent(
                  agentName || "Unknown Agent",
                  30
                ) ? (
                  <Tooltip
                    withArrow
                    content={agentName || "Unknown Agent"}
                    relationship="label"
                  >
                    <BreadcrumbButton
                      onClick={() => navigate(`/agents/${evaluation.agent_id}`)}
                    >
                      {truncateBreadcrumbLongName(agentName || "Unknown Agent")}
                    </BreadcrumbButton>
                  </Tooltip>
                ) : (
                  <BreadcrumbButton
                    onClick={() => navigate(`/agents/${evaluation.agent_id}`)}
                  >
                    {agentName || "Unknown Agent"}
                  </BreadcrumbButton>
                )}
              </BreadcrumbItem>
              <BreadcrumbDivider />
              <BreadcrumbItem>
                {isTruncatableBreadcrumbContent(
                  evaluationName || evaluation.name,
                  30
                ) ? (
                  <Tooltip
                    withArrow
                    content={evaluationName || evaluation.name}
                    relationship="label"
                  >
                    <BreadcrumbButton current>
                      {truncateBreadcrumbLongName(
                        evaluationName || evaluation.name
                      )}
                    </BreadcrumbButton>
                  </Tooltip>
                ) : (
                  <BreadcrumbButton current>
                    {evaluationName || evaluation.name}
                  </BreadcrumbButton>
                )}
              </BreadcrumbItem>
            </Breadcrumb>
            <h1 className="text-2xl font-bold">
              {evaluationName || evaluation.name}
            </h1>
            <p className="text-sm text-muted-foreground">
              Evaluation run on{" "}
              {new Date(evaluation.created_at).toLocaleString()}
            </p>
            <AIContentDisclaimer />
          </div>
        </div>
      </div>

      {/* Show progress bar for running/pending evaluations */}
      {(evaluation.status === "running" || evaluation.status === "pending") && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-2">
                  <CircleNotch size={16} className="animate-spin" />
                  {evaluation.status === "pending" ? "Preparing" : "Progress"}
                </span>
                <span className="font-medium">
                  {evaluation.completed_tests} / {evaluation.total_tests} tests
                  completed
                </span>
              </div>
              <div className="relative">
                <Progress value={progressPercentage} className="h-2" />
                {/* Animated shimmer overlay to show activity */}
                <div className="absolute inset-0 overflow-hidden rounded-full">
                  <div className="h-full w-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                </div>
              </div>
              <p className="text-xs text-muted-foreground text-center animate-pulse">
                {evaluation.status === "pending"
                  ? "Starting evaluation"
                  : "Running tests"}
                <span className="inline-block w-3 text-left">
                  <span className="animate-dots">.</span>
                  <span className="animate-dots animation-delay-200">.</span>
                  <span className="animate-dots animation-delay-400">.</span>
                </span>
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary statistics matching design */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-500">
              {evaluation.total_tests}
            </div>
            <p className="text-sm text-muted-foreground">Total Test Cases</p>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-500">
              {evaluation.passed_count}
            </div>
            <p className="text-sm text-muted-foreground">Passed</p>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-500">
              {evaluation.failed_tests}
            </div>
            <p className="text-sm text-muted-foreground">Failed</p>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-500">
              {passRate === "N/A" ? passRate : `${passRate}%`}
            </div>
            <p className="text-sm text-muted-foreground">Pass Rate</p>
          </div>
        </Card>
      </div>

      {/* Show test results if available */}
      {evaluation.test_cases && evaluation.test_cases.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Test Results</h2>

          <div className="grid grid-cols-1 gap-3">
            {evaluation.test_cases.map((testCase, index) => (
              <Card
                key={testCase.testcase_id}
                className="cursor-pointer transition-all border-indigo-100/70 shadow-indigo-50/30 shadow-sm hover:shadow-indigo-100/50 hover:shadow-md"
                onClick={(event) =>
                  handleTestCaseClick(testCase.testcase_id, event)
                }
                style={{ userSelect: "text" }}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Document20Regular className="text-gray-600" />
                      <div>
                        <h3 className="font-medium">
                          {getTestCaseName(testCase.testcase_id)}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {evaluation.created_at
                            ? new Date(evaluation.created_at).toLocaleString()
                            : "No date available"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={testCase.passed ? "default" : "destructive"}
                        className="text-xs"
                        style={{
                          backgroundColor: testCase.passed
                            ? "#F1FAF1"
                            : "#FDF6F6",
                          color: testCase.passed ? "#0D7717" : "#C4314B",
                          borderRadius: "4px",
                          padding: "2px 4px",
                        }}
                      >
                        {testCase.passed ? "Passed" : "Failed"}
                      </Badge>
                    </div>
                  </div>

                  {testCase.response_from_agent && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-sm text-gray-700 line-clamp-2">
                        {testCase.response_from_agent}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Show message if no results yet */}
      {(!evaluation.test_cases || evaluation.test_cases.length === 0) &&
        evaluation.status !== "failed" && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              {evaluation.status === "running" ||
              evaluation.status === "pending" ? (
                <>
                  <CircleNotch
                    size={48}
                    className="animate-spin text-primary mb-4"
                  />
                  <p className="text-muted-foreground font-medium">
                    {evaluation.status === "pending"
                      ? "Preparing evaluation..."
                      : "Evaluation is starting..."}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Test results will appear here as they complete
                  </p>
                  <div className="mt-4 flex items-center gap-1 text-xs text-muted-foreground">
                    <span>Running</span>
                    <span className="animate-dots">.</span>
                    <span className="animate-dots animation-delay-200">.</span>
                    <span className="animate-dots animation-delay-400">.</span>
                  </div>
                </>
              ) : (
                <>
                  <Clock size={48} className="text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    No test results available yet
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        )}

      {/* Show error message if evaluation failed */}
      {evaluation.status === "failed" && (
        <Alert>
          <AlertDescription style={{ color: "#C4314B" }}>
            This evaluation run failed. Please check the logs for more
            information.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
