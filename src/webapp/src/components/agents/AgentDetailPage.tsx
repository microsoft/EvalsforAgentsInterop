import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect, useMemo } from "react";
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
  CircleNotch,
  Trash,
  DotsThree,
  Play,
} from "@phosphor-icons/react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import {
  SearchFilterControls,
  FilterOption,
} from "@/components/shared/SearchFilterControls";
import { toast } from "sonner";
import { useTableState } from "@/hooks/useTableState";
import { apiClient } from "@/lib/api";
import { Agent } from "@/lib/types";
import { useAgentEvaluations } from "@/hooks/useAgentEvaluations";
import { useDatasets } from "@/hooks/useDatasets";
import { useSelectableClick } from "@/hooks/useSelectableClick";
import { getKeyboardProps } from "@/hooks/useKeyboardClick";

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter and sort state
  const [selectedDatasetFilters, setSelectedDatasetFilters] = useState<
    string[]
  >([]);

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [evaluationToDelete, setEvaluationToDelete] = useState<any>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Run evaluation state
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [verboseLogging, setVerboseLogging] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);
  const { createClickHandler } = useSelectableClick();

  // Fetch evaluations for this agent
  const {
    evaluations,
    loading: evaluationsLoading,
    refetch: refetchEvaluations,
  } = useAgentEvaluations(id);

  // Fetch datasets to get dataset names
  const {
    datasets,
    loading: datasetsLoading,
    error: datasetsError,
  } = useDatasets();

  useEffect(() => {
    const fetchAgent = async () => {
      if (!id) {
        setError("Agent ID is required");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const fetchedAgent = await apiClient.getAgent(id);
        setAgent(fetchedAgent);
        setError(null); // Clear any previous errors
      } catch (error) {
        console.error("Error fetching agent:", error);
        setError(
          error instanceof Error
            ? error.message
            : "Failed to load agent details"
        );
      } finally {
        setIsLoading(false);
      }
    };

    fetchAgent();
  }, [id]);

  // Process evaluation data with enhanced information
  const processedEvaluations = useMemo(() => {
    if (!evaluations || !datasets) return { entries: [], datasets: [] };

    // Helper function to get dataset name by ID
    const getDatasetName = (datasetId: string) => {
      const dataset = datasets?.find((s) => s.id === datasetId);
      return dataset?.seed?.name || "Unknown Dataset";
    };

    const entries = evaluations.map((evaluation) => {
      const passRate =
        evaluation.total_tests > 0
          ? (evaluation.passed_count / evaluation.total_tests) * 100
          : 0;
      const datasetName = getDatasetName(evaluation.dataset_id);
      const evaluationDate = new Date(evaluation.created_at);

      return {
        ...evaluation,
        passRate,
        passRateDisplay: `${Math.round(passRate)}%`,
        datasetName,
        date: evaluationDate,
        dateDisplay: `${evaluationDate.toLocaleDateString("en-US", {
          month: "numeric",
          day: "numeric",
        })}, ${evaluationDate.toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
          hour12: true,
        })}`,
      };
    });

    // Extract unique datasets for filter
    const uniqueDatasets = Array.from(
      new Set(entries.map((entry) => entry.datasetName))
    ).sort();

    return { entries, datasets: uniqueDatasets };
  }, [evaluations, datasets]);

  // Apply filters and sorting using useTableState
  const {
    searchTerm,
    setSearchTerm,
    sortOrder,
    handleSort,
    filteredData: filteredEvaluations,
  } = useTableState({
    data: processedEvaluations.entries,
    searchFields: ["name"],
    defaultSortField: "date",
    initialSortOrder: "desc", // Newest first
    customSortFunction: (a: any, b: any, order: "asc" | "desc" | "none") => {
      // Sort by creation date - newest first (desc) or oldest first (asc)
      const dateComparison = b.date.getTime() - a.date.getTime(); // b - a for newest first

      if (order === "desc" || order === "none") {
        return dateComparison; // Newest first
      } else {
        return -dateComparison; // Oldest first
      }
    },
    filters: {
      dataset: {
        getValue: (entry: any) => entry.datasetName,
        selectedValues: selectedDatasetFilters,
      },
    },
  });

  // Delete evaluation handlers
  const handleDeleteEvaluation = (evaluation: any) => {
    setEvaluationToDelete(evaluation);
    setDeleteDialogOpen(true);
  };

  const handleEvaluationClick = createClickHandler((evaluationId: string) => {
    navigate(`/evaluations/${evaluationId}`);
  });

  const confirmDeleteEvaluation = async () => {
    if (!evaluationToDelete) return;

    setIsDeleting(true);
    try {
      await apiClient.deleteEvaluation(evaluationToDelete.id);
      toast.success("Evaluation deleted successfully");
      setDeleteDialogOpen(false);
      setEvaluationToDelete(null);
      // Refresh the evaluations list to reflect the deletion
      await refetchEvaluations();
    } catch (error) {
      console.error("Error deleting evaluation:", error);
      toast.error("Failed to delete evaluation");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleStartEvaluation = async () => {
    if (!selectedDataset || !agent) {
      toast.error("Please select a dataset first");
      return;
    }

    setIsRunningEvaluation(true);
    try {
      const dataset = datasets?.find((s) => s.id === selectedDataset);

      if (!dataset) {
        toast.error("Dataset not found");
        return;
      }

      // Create the evaluation run
      const evaluationRun = await apiClient.createEvaluation({
        name: `${agent.name} - ${dataset.seed.name}`,
        dataset_id: selectedDataset,
        agent_id: agent.id,
        agent_endpoint: agent.agent_invocation_url,
        agent_auth_required: true,
        timeout_seconds: 300,
        verbose_logging: verboseLogging,
      });

      toast.success(`Evaluation started: ${evaluationRun.name}`, {
        description: `Running ${dataset.test_case_ids.length} test cases`,
      });

      setRunDialogOpen(false);
      setSelectedDataset("");
      setVerboseLogging(false);

      // Navigate to the evaluation detail page
      navigate(`/evaluations/${evaluationRun.id}`);
    } catch (error) {
      console.error("Error starting evaluation:", error);
      toast.error("Failed to start evaluation", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsRunningEvaluation(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <CircleNotch size={48} className="animate-spin text-primary mb-4" />
        <p className="text-muted-foreground">Loading agent details...</p>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/agents")}
            className="gap-2"
          >
            <ArrowLeft size={16} />
            Back to Agents
          </Button>
        </div>
        <Alert>
          <AlertDescription>{error || "Agent not found"}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h2 className="text-2xl font-bold mb-2">Agent not found</h2>
        <p className="text-muted-foreground mb-6">
          The agent you're looking for doesn't exist.
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
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
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
              {isTruncatableBreadcrumbContent(agent.name, 30) ? (
                <Tooltip withArrow content={agent.name} relationship="label">
                  <BreadcrumbButton current>
                    {truncateBreadcrumbLongName(agent.name)}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton current>{agent.name}</BreadcrumbButton>
              )}
            </BreadcrumbItem>
          </Breadcrumb>
          <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
          <p className="text-muted-foreground">{agent.description}</p>
          <div className="flex items-center gap-2 pt-2">
            {agent.model && (
              <>
                <span className="text-sm text-muted-foreground">Model:</span>
                <Badge
                  variant="secondary"
                  style={{
                    display: "flex",
                    width: "103px",
                    padding: "2px 4px",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: "2px",
                    flexShrink: 0,
                    borderRadius: "4px",
                    background: "#EBEBEB",
                    color: "#6B7280",
                    border: "none",
                  }}
                >
                  {agent.model}
                </Badge>
                <span className="text-sm text-muted-foreground">•</span>
              </>
            )}
            <span className="text-sm text-muted-foreground">
              Registered
              {agent.createdAt
                ? new Date(agent.createdAt).toLocaleDateString()
                : "Unknown"}
            </span>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold">Evaluation History</h2>

        {evaluationsLoading ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <CircleNotch
                size={32}
                className="animate-spin text-primary mb-2"
              />
              <p className="text-muted-foreground">Loading evaluations...</p>
            </CardContent>
          </Card>
        ) : processedEvaluations.entries.length === 0 ? (
          <div className="space-y-6">
            <div className="flex justify-end">
              <Button onClick={() => setRunDialogOpen(true)} className="gap-2">
                <Play size={16} />
                Run Evals
              </Button>
            </div>
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <p className="text-muted-foreground">No evaluation runs yet</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Click "Run Evals" above to start your first evaluation
                </p>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Search and Filter Controls with Run Evals Button */}
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1">
                <SearchFilterControls
                  searchValue={searchTerm}
                  onSearchChange={setSearchTerm}
                  searchPlaceholder="Search evaluations"
                  filters={[
                    {
                      key: "dataset",
                      placeholder: "Evaluation dataset",
                      options: processedEvaluations.datasets,
                      selectedOptions: selectedDatasetFilters,
                      onSelectionChange: setSelectedDatasetFilters,
                      multiselect: true,
                      minWidth: "200px",
                    },
                  ]}
                  sortOrder={sortOrder}
                  onSortChange={handleSort}
                  sortLabel="Latest Runs"
                />
              </div>
              <Button
                onClick={() => setRunDialogOpen(true)}
                className="gap-2 min-h-[40px] px-4 py-1.5"
                style={{ marginTop: "48px" }}
              >
                <Play size={16} />
                Run Evals
              </Button>
            </div>

            {filteredEvaluations.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <p className="text-muted-foreground">
                    No evaluations match your search criteria
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Try adjusting your filters or search terms
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {filteredEvaluations.map((evaluation) => {
                  const keyboardProps = getKeyboardProps((event) =>
                    handleEvaluationClick(evaluation.id, event)
                  );
                  return (
                    <Card
                      key={evaluation.id}
                      className="cursor-pointer transition-all hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                      {...keyboardProps}
                      style={{ userSelect: "text" }}
                    >
                      <CardHeader>
                        <div
                          className="flex items-center justify-between gap-4"
                          style={{ minWidth: 0 }}
                        >
                          <div className="flex-1 min-w-0">
                            <div
                              className="text-sm font-semibold text-blue-600 mb-1"
                              style={{
                                wordWrap: "break-word",
                                whiteSpace: "normal",
                                overflowWrap: "break-word",
                              }}
                            >
                              {evaluation.dateDisplay}
                            </div>
                            <div
                              className="flex items-center gap-2 mb-1"
                              style={{ minWidth: 0 }}
                            >
                              <CardTitle
                                className="text-lg"
                                style={{
                                  wordWrap: "break-word",
                                  whiteSpace: "normal",
                                  overflowWrap: "break-word",
                                  minWidth: 0,
                                  flex: 1,
                                }}
                              >
                                {evaluation.name}
                              </CardTitle>
                              <Badge
                                variant={
                                  evaluation.status === "completed"
                                    ? "default"
                                    : evaluation.status === "running"
                                    ? "secondary"
                                    : evaluation.status === "failed"
                                    ? "destructive"
                                    : "outline"
                                }
                                className="text-xs"
                                style={
                                  evaluation.status === "completed"
                                    ? {
                                        backgroundColor: "#F1FAF1",
                                        color: "#0D7717",
                                        borderRadius: "4px",
                                        padding: "2px 4px",
                                      }
                                    : {}
                                }
                              >
                                {evaluation.status.charAt(0).toUpperCase() +
                                  evaluation.status.slice(1)}
                              </Badge>
                            </div>
                            <CardDescription
                              style={{
                                wordWrap: "break-word",
                                whiteSpace: "normal",
                                overflowWrap: "break-word",
                              }}
                            >
                              {evaluation.datasetName} •{" "}
                              {evaluation.total_tests} test
                              {evaluation.total_tests !== 1 ? "s" : ""}
                            </CardDescription>
                          </div>
                          <div className="flex items-center gap-3">
                            {evaluation.status === "completed" && (
                              <Badge
                                variant="secondary"
                                style={{
                                  display: "flex",
                                  width: "fit-content",
                                  padding: "2px 8px",
                                  justifyContent: "center",
                                  alignItems: "center",
                                  gap: "2px",
                                  flexShrink: 0,
                                  borderRadius: "4px",
                                  background:
                                    evaluation.passRate >= 80
                                      ? "#F1FAF1"
                                      : "#FDF6F6",
                                  color:
                                    evaluation.passRate >= 80
                                      ? "#0D7717"
                                      : "#C4314B",
                                  border: "none",
                                }}
                                className="text-lg font-medium px-3 py-1"
                              >
                                {evaluation.passRateDisplay}
                              </Badge>
                            )}
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => e.stopPropagation()}
                                  aria-label="Evaluation options"
                                >
                                  <DotsThree size={16} />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteEvaluation(evaluation);
                                  }}
                                  variant="destructive"
                                >
                                  <Trash size={16} className="mr-2" />
                                  Delete Evaluation Run
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      </CardHeader>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Delete Evaluation Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Evaluation</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this evaluation? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteEvaluation}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Run Evaluation Modal */}
      <Dialog open={runDialogOpen} onOpenChange={setRunDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Run Evaluation</DialogTitle>
            <DialogDescription>
              Select an evaluation dataset to test this agent
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="space-y-2">
              <Label htmlFor="dataset">Evaluation Dataset</Label>
              {datasetsLoading ? (
                <div className="flex items-center gap-2">
                  <CircleNotch size={16} className="animate-spin" />
                  <span className="text-sm text-muted-foreground">
                    Loading datasets...
                  </span>
                </div>
              ) : datasetsError ? (
                <Alert>
                  <AlertDescription>
                    Failed to load datasets. Please try again later.
                  </AlertDescription>
                </Alert>
              ) : (
                <select
                  id="dataset"
                  title="Select evaluation dataset"
                  value={selectedDataset}
                  onChange={(e) => setSelectedDataset(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="">Select a dataset</option>
                  {datasets?.map((dataset) => (
                    <option key={dataset.id} value={dataset.id}>
                      {dataset.seed.name} ({dataset.test_case_ids.length} test
                      cases)
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="flex items-center space-x-2 pt-2">
              <input
                type="checkbox"
                id="verboseLogging"
                checked={verboseLogging}
                onChange={(e) => setVerboseLogging(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label htmlFor="verboseLogging" className="text-sm font-normal cursor-pointer">
                Verbose logging (show each assertion in activity log)
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRunDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={
                !selectedDataset || datasetsLoading || isRunningEvaluation
              }
              onClick={handleStartEvaluation}
            >
              {isRunningEvaluation ? (
                <>
                  <CircleNotch size={16} className="animate-spin mr-2" />
                  Starting...
                </>
              ) : (
                "Run Evaluation"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
