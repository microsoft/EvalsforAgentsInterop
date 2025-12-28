import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
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
  X,
  Warning,
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
import { apiClient } from "@/lib/api";

const useBreadcrumbStyles = makeStyles({
  // Remove custom styles since we're using Fluent UI's built-in truncation
});

export function EvaluationResultsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const breadcrumbStyles = useBreadcrumbStyles();
  const { evaluation, testCases, loading, error, refetch } = useEvaluation(id, true); // Enable polling
  const { agents } = useAgents();
  const { datasets } = useDatasets();
  const { createClickHandler } = useSelectableClick();
  const [isCancelling, setIsCancelling] = useState(false);

  // Handler to cancel the evaluation
  const handleCancel = async () => {
    if (!id) return;
    setIsCancelling(true);
    try {
      await apiClient.cancelEvaluation(id);
      refetch(); // Refresh the evaluation data
    } catch (err) {
      console.error("Failed to cancel evaluation:", err);
    } finally {
      setIsCancelling(false);
    }
  };

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

      {/* Show rate limit warnings if any */}
      {evaluation.warnings && evaluation.warnings.length > 0 && (
        <Alert>
          <AlertDescription className="flex items-start gap-2" style={{ color: "#9E6A03" }}>
            <Warning size={18} className="mt-0.5 flex-shrink-0" />
            <div>
              <strong>Rate Limit Warnings:</strong>
              <ul className="mt-1 ml-4 list-disc">
                {evaluation.warnings.slice(0, 5).map((warning, index) => (
                  <li key={index} className="text-sm">{warning}</li>
                ))}
                {evaluation.warnings.length > 5 && (
                  <li className="text-sm text-muted-foreground">
                    ...and {evaluation.warnings.length - 5} more warning(s)
                  </li>
                )}
              </ul>
            </div>
          </AlertDescription>
        </Alert>
      )}

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
                {evaluation.status_message || (evaluation.status === "pending"
                  ? "Starting evaluation"
                  : "Running tests")}
                <span className="inline-block w-3 text-left">
                  <span className="animate-dots">.</span>
                  <span className="animate-dots animation-delay-200">.</span>
                  <span className="animate-dots animation-delay-400">.</span>
                </span>
              </p>
              
              {/* Rate Limit Statistics */}
              {(evaluation.total_rate_limit_hits ?? 0) > 0 && (
                <div className="mt-3 p-2 bg-amber-50 dark:bg-amber-950/30 rounded-md">
                  <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1">
                      <Warning size={12} className="text-amber-600" />
                      <span className="text-amber-700 dark:text-amber-400">
                        <strong>{evaluation.total_rate_limit_hits}</strong> rate limit hit(s)
                      </span>
                    </div>
                    <div className="text-amber-600 dark:text-amber-500">
                      <strong>{evaluation.total_retry_wait_seconds?.toFixed(1) ?? 0}s</strong> total wait time
                    </div>
                  </div>
                </div>
              )}
              
              {/* Status History Timeline */}
              {evaluation.status_history && evaluation.status_history.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <details className="group">
                    <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
                      <Clock size={12} />
                      <span>Activity Log ({evaluation.status_history.length} entries
                        {(evaluation.total_rate_limit_hits ?? 0) > 0 && 
                          `, ${evaluation.total_rate_limit_hits} retries`
                        }
                      )</span>
                    </summary>
                    <div className="mt-2 max-h-40 overflow-y-auto">
                      <div className="space-y-1">
                        {evaluation.status_history.slice().reverse().map((entry, index) => (
                          <div 
                            key={index} 
                            className={`text-xs py-1 px-2 rounded flex items-start gap-2 ${
                              entry.is_rate_limit 
                                ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400' 
                                : index === 0 
                                  ? 'bg-primary/10 text-primary' 
                                  : 'text-muted-foreground'
                            }`}
                          >
                            <span className="shrink-0 font-mono text-[10px] opacity-70">
                              {new Date(entry.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="break-words flex-1">{entry.message}</span>
                            {entry.is_rate_limit && entry.wait_seconds && (
                              <span className="shrink-0 text-[10px] font-mono bg-amber-200 dark:bg-amber-800 px-1 rounded">
                                +{entry.wait_seconds.toFixed(1)}s
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </details>
                </div>
              )}
              
              <div className="flex justify-center pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  disabled={isCancelling}
                  className="gap-2 text-destructive hover:text-destructive"
                >
                  {isCancelling ? (
                    <CircleNotch size={14} className="animate-spin" />
                  ) : (
                    <X size={14} />
                  )}
                  {isCancelling ? "Cancelling..." : "Cancel Evaluation"}
                </Button>
              </div>
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

      {/* Status History for completed evaluations */}
      {evaluation.status !== "running" && evaluation.status !== "pending" && 
       evaluation.status_history && evaluation.status_history.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock size={18} />
              Evaluation Activity Log
            </CardTitle>
            <CardDescription className="flex items-center gap-4">
              <span>{evaluation.status_history.length} steps completed</span>
              {(evaluation.total_rate_limit_hits ?? 0) > 0 && (
                <span className="flex items-center gap-2 text-amber-600">
                  <Warning size={14} />
                  {evaluation.total_rate_limit_hits} rate limit hit(s) • {evaluation.total_retry_wait_seconds?.toFixed(1) ?? 0}s total wait
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-h-48 overflow-y-auto">
              <div className="space-y-1">
                {evaluation.status_history.map((entry, index) => (
                  <div 
                    key={index} 
                    className={`text-sm py-1.5 px-3 rounded flex items-start gap-3 hover:bg-muted/50 ${
                      entry.is_rate_limit 
                        ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400' 
                        : ''
                    }`}
                  >
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={entry.is_rate_limit ? '' : 'text-muted-foreground'}>{entry.message}</span>
                    {entry.is_rate_limit && entry.wait_seconds && (
                      <span className="shrink-0 text-xs font-mono bg-amber-200 dark:bg-amber-800 px-1.5 py-0.5 rounded ml-auto">
                        +{entry.wait_seconds.toFixed(1)}s
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
                        <p className="text-sm text-muted-foreground flex items-center gap-2">
                          <span>
                            {testCase.completed_at
                              ? new Date(testCase.completed_at).toLocaleString()
                              : evaluation.created_at
                                ? new Date(evaluation.created_at).toLocaleString()
                                : "No date available"}
                          </span>
                          {/* Timing information */}
                          {testCase.total_duration_seconds != null && (
                            <span className="text-xs text-muted-foreground/70 font-mono">
                              ⏱ {testCase.total_duration_seconds.toFixed(1)}s
                              {testCase.agent_call_duration_seconds != null && testCase.judge_call_duration_seconds != null && (
                                <span className="ml-1 opacity-70">
                                  (agent: {testCase.agent_call_duration_seconds.toFixed(1)}s, judge: {testCase.judge_call_duration_seconds.toFixed(1)}s)
                                </span>
                              )}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Show retry indicator if there were rate limit retries */}
                      {testCase.retry_count && testCase.retry_count > 0 && (
                        <Tooltip
                          withArrow
                          content={`${testCase.retry_count} retry(ies) due to rate limits`}
                          relationship="label"
                        >
                          <Badge
                            variant="outline"
                            className="text-xs flex items-center gap-1"
                            style={{
                              backgroundColor: "#FFFBEB",
                              color: "#9E6A03",
                              borderColor: "#FCD34D",
                              borderRadius: "4px",
                              padding: "2px 6px",
                            }}
                          >
                            <Warning size={12} />
                            {testCase.retry_count}×
                          </Badge>
                        </Tooltip>
                      )}
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
        evaluation.status !== "failed" &&
        evaluation.status !== "cancelled" && (
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

      {/* Show message if evaluation was cancelled */}
      {evaluation.status === "cancelled" && (
        <Alert>
          <AlertDescription style={{ color: "#9E6A03" }}>
            This evaluation was cancelled. Completed tests: {evaluation.completed_tests} / {evaluation.total_tests}.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
