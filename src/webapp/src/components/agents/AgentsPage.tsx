import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Plus,
  Robot,
  Play,
  CircleNotch,
  DotsThree,
  PencilSimple,
  Trash,
} from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAgents } from "@/hooks/useAgents";
import { useDatasets } from "@/hooks/useDatasets";
import { apiClient } from "@/lib/api";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AgentForm } from "./AgentForm";
import { Agent } from "@/lib/types";
import { getAgentIcon } from "@/lib/agentIcons";
import { FolderOpen20Regular } from "@fluentui/react-icons";
import { DataTable, TableColumn } from "@/components/shared/DataTable";
import {
  SearchFilterControls,
  FilterOption,
} from "@/components/shared/SearchFilterControls";
import { NoDataCard } from "@/components/shared/NoDataCard";
import { useTableState } from "@/hooks/useTableState";

export function AgentsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    agents,
    loading: isLoading,
    error,
    refetch: refetchAgents,
  } = useAgents();
  const {
    datasets,
    loading: datasetsLoading,
    error: datasetsError,
  } = useDatasets();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [isCreating, setIsCreating] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedModelFilters, setSelectedModelFilters] = useState<string[]>(
    []
  );
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);

  const availableModels = Array.from(
    new Set(agents.map((agent) => agent.model).filter((model) => model))
  ).sort();

  // Handle edit query parameter
  useEffect(() => {
    const editAgentId = searchParams.get("edit");
    if (editAgentId && agents.length > 0) {
      const agentToEdit = agents.find((agent) => agent.id === editAgentId);
      if (agentToEdit) {
        setEditingAgent(agentToEdit);
        setEditDialogOpen(true);
        // Clear the query parameter
        setSearchParams(new URLSearchParams());
      }
    }
  }, [agents, searchParams, setSearchParams]);

  const {
    searchTerm,
    setSearchTerm,
    sortOrder,
    handleSort,
    filteredData: filteredAgents,
  } = useTableState({
    data: agents,
    searchFields: ["name"],
    defaultSortField: "name",
    filters: {
      model: {
        getValue: (agent: Agent) => agent.model,
        selectedValues: selectedModelFilters,
      },
    },
  });

  // Define table columns
  const columns: TableColumn[] = [
    {
      key: "name",
      header: "Agent name",
      width: "45%",
      minWidth: "250px",
      render: (agent: Agent) => (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            boxSizing: "border-box",
            minWidth: 0,
            width: "100%",
          }}
        >
          <img
            src={getAgentIcon(agent.id)}
            alt="Agent logo"
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "6px",
              flexShrink: 0,
            }}
          />
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "2px",
              minWidth: 0,
              flex: 1,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                fontWeight: 600,
                fontSize: "14px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {agent.name}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "#6b7280",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {agent.description}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: "registered",
      header: "Registered",
      width: "15%",
      minWidth: "120px",
      render: (agent: Agent) => new Date(agent.createdAt).toLocaleDateString(),
    },
    {
      key: "model",
      header: "Model",
      width: "20%",
      minWidth: "140px",
      render: (agent: Agent) => (
        <div
          style={{ display: "flex", alignItems: "center", minWidth: "129px" }}
        >
          <Badge
            variant="secondary"
            style={{
              display: "flex",
              width: "fit-content",
              padding: "0 8px 2px 8px",
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
            {agent.model || "Unknown"}
          </Badge>
        </div>
      ),
    },
    {
      key: "actions",
      header: "Action",
      width: "20%",
      minWidth: "160px",
      render: (agent: Agent) => (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            minWidth: "40px",
          }}
        >
          <Button
            onClick={(e) => {
              e.stopPropagation();
              handleRunEvals(agent.id);
            }}
            size="sm"
            className="gap-2"
          >
            <Play size={16} />
            Run Evals
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => e.stopPropagation()}
              >
                <DotsThree size={16} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  handleOpenAgent(agent);
                }}
              >
                <FolderOpen20Regular className="mr-2" />
                Open Agent
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  handleEditAgent(agent);
                }}
              >
                <PencilSimple size={16} className="mr-2" />
                Edit Agent
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteAgent(agent);
                }}
                style={{ color: "#C4314B" }}
              >
                <Trash size={16} className="mr-2" />
                Delete Agent
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ),
    },
  ];

  const filters: FilterOption[] = [
    {
      key: "model",
      placeholder: "Model type",
      options: availableModels,
      selectedOptions: selectedModelFilters,
      onSelectionChange: setSelectedModelFilters,
      multiselect: true,
      minWidth: "180px",
    },
  ];

  const handleOpenAgent = (agent: Agent) => {
    navigate(`/agents/${agent.id}`);
  };

  const handleEditAgent = (agent: Agent) => {
    setEditingAgent(agent);
    setEditDialogOpen(true);
  };

  const handleDeleteAgent = (agent: Agent) => {
    setAgentToDelete(agent);
    setDeleteDialogOpen(true);
  };

  const handleCreateAgent = async (data: {
    name: string;
    description: string;
    model: string;
    agent_invocation_url: string;
  }) => {
    setIsCreating(true);
    try {
      await apiClient.createAgent({
        name: data.name,
        description: data.description,
        model: data.model,
        agent_invocation_url: data.agent_invocation_url,
      });
      toast.success("Agent registered successfully");
      setDialogOpen(false);
      refetchAgents();
    } catch (error) {
      console.error("Error creating agent:", error);
      toast.error("Failed to register agent");
    } finally {
      setIsCreating(false);
    }
  };

  const handleUpdateAgent = async (data: {
    name: string;
    description: string;
    model: string;
    agent_invocation_url: string;
  }) => {
    if (!editingAgent) return;

    setIsCreating(true);
    try {
      await apiClient.updateAgent(editingAgent.id, {
        name: data.name,
        description: data.description,
        model: data.model,
        agent_invocation_url: data.agent_invocation_url,
      });
      toast.success("Agent updated successfully");
      setEditDialogOpen(false);
      setEditingAgent(null);
      refetchAgents();
    } catch (error) {
      console.error("Error updating agent:", error);
      toast.error("Failed to update agent");
    } finally {
      setIsCreating(false);
    }
  };

  const confirmDeleteAgent = async () => {
    if (!agentToDelete) return;

    setIsDeleting(true);
    try {
      await apiClient.deleteAgent(agentToDelete.id);
      toast.success("Agent deleted successfully");
      setDeleteDialogOpen(false);
      setAgentToDelete(null);
      refetchAgents();
    } catch (error) {
      console.error("Error deleting agent:", error);
      toast.error("Failed to delete agent");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRunEvals = (agentId: string) => {
    setSelectedAgent(agentId);
    setSelectedDataset(""); // Reset selected dataset
    setRunDialogOpen(true);
  };

  const handleStartEvaluation = async () => {
    if (!selectedAgent || !selectedDataset) {
      toast.error("Please select a dataset first");
      return;
    }

    setIsRunningEvaluation(true);
    try {
      const agent = agents.find((a) => a.id === selectedAgent);
      const dataset = datasets.find((s) => s.id === selectedDataset);

      if (!agent || !dataset) {
        toast.error("Agent or dataset not found");
        return;
      }

      // Create the evaluation run
      const evaluationRun = await apiClient.createEvaluation({
        name: `${agent.name} - ${dataset.seed.name}`,
        dataset_id: selectedDataset,
        agent_id: selectedAgent,
        agent_endpoint: agent.agent_invocation_url,
        agent_auth_required: true,
        timeout_seconds: 300,
      });

      toast.success(`Evaluation started: ${evaluationRun.name}`, {
        description: `Running ${dataset.test_case_ids.length} test cases`,
      });

      setRunDialogOpen(false);
      setSelectedDataset("");
      setSelectedAgent(null);

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
        <p className="text-muted-foreground">Loading agents...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
            <p className="text-muted-foreground mt-1">
              Manage and evaluate AI agents across different test suites
            </p>
          </div>
        </div>
        <NoDataCard
          icon={<Robot size={48} className="text-muted-foreground mb-4" />}
          title="Failed to load agents"
          description={`Please try again later. ${error}`}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground mt-1">
            Manage and evaluate AI agents across different test suites
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus size={18} weight="bold" />
              Register Agent
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Register New Agent</DialogTitle>
              <DialogDescription>
                Add a new AI agent to evaluate against your test datasets
              </DialogDescription>
            </DialogHeader>
            <AgentForm
              mode="create"
              onSubmit={handleCreateAgent}
              onCancel={() => setDialogOpen(false)}
              isLoading={isCreating}
            />
          </DialogContent>
        </Dialog>
      </div>

      {agents.length === 0 ? (
        <NoDataCard
          icon={<Robot size={48} className="text-muted-foreground mb-4" />}
          title="No agents registered yet"
          action={
            <Button
              onClick={() => setDialogOpen(true)}
              variant="outline"
              className="gap-2"
            >
              <Plus size={18} />
              Register Your First Agent
            </Button>
          }
        />
      ) : (
        <>
          <SearchFilterControls
            searchValue={searchTerm}
            onSearchChange={setSearchTerm}
            searchPlaceholder="Search agents"
            filters={filters}
            sortOrder={sortOrder}
            onSortChange={handleSort}
            sortLabel="Sort"
          />
          <DataTable
            columns={columns}
            data={filteredAgents}
            onRowClick={handleOpenAgent}
            emptyState={
              <NoDataCard
                icon={
                  <Robot size={48} className="text-muted-foreground mb-4" />
                }
                title={`No agents found matching "${searchTerm}"`}
                description="Try adjusting your search terms or filters"
              />
            }
          />
        </>
      )}

      {/* Run Evaluation Modal */}
      <Dialog open={runDialogOpen} onOpenChange={setRunDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Run Evaluation</DialogTitle>
            <DialogDescription>
              Select an evaluation dataset to test this agent
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
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
                  {datasets.map((dataset) => (
                    <option key={dataset.id} value={dataset.id}>
                      {dataset.seed.name} ({dataset.test_case_ids.length} test
                      cases)
                    </option>
                  ))}
                </select>
              )}
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

      {/* Edit Agent Modal */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Agent</DialogTitle>
            <DialogDescription>
              Update the agent's information
            </DialogDescription>
          </DialogHeader>
          <AgentForm
            mode="edit"
            initialData={editingAgent || undefined}
            onSubmit={handleUpdateAgent}
            onCancel={() => {
              setEditDialogOpen(false);
              setEditingAgent(null);
            }}
            isLoading={isCreating}
          />
        </DialogContent>
      </Dialog>

      {/* Delete Agent Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Agent</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{agentToDelete?.name}"?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setDeleteDialogOpen(false);
                setAgentToDelete(null);
              }}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteAgent}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <CircleNotch size={16} className="animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                "Delete Agent"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
