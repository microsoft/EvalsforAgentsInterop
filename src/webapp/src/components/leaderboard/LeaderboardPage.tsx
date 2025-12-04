import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Trophy, CircleNotch } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@fluentui/react-components";
import { DataTable, TableColumn } from "@/components/shared/DataTable";
import {
  SearchFilterControls,
  FilterOption,
} from "@/components/shared/SearchFilterControls";
import { NoDataCard } from "@/components/shared/NoDataCard";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { useTableState } from "@/hooks/useTableState";
import { useEvaluations } from "@/hooks/useEvaluations";
import { useAgents } from "@/hooks/useAgents";
import { useDatasets } from "@/hooks/useDatasets";
import { EvaluationRun } from "@/lib/api";
import { getAgentIcon } from "@/lib/agentIcons";

export function LeaderboardPage() {
  const navigate = useNavigate();

  const [selectedDatasetFilters, setSelectedDatasetFilters] = useState<
    string[]
  >([]);
  const [selectedModelFilters, setSelectedModelFilters] = useState<string[]>(
    []
  );

  const {
    evaluations,
    loading: evaluationsLoading,
    error: evaluationsError,
  } = useEvaluations();
  const { agents, loading: agentsLoading, error: agentsError } = useAgents();
  const {
    datasets,
    loading: datasetsLoading,
    error: datasetsError,
  } = useDatasets();

  // Compute processed data using useMemo
  const processedData = useMemo(() => {
    if (!evaluations || !agents || !datasets) {
      return { entries: [], datasets: [], models: [] };
    }

    // Create lookup maps
    const agentMap = new Map(agents.map((agent: any) => [agent.id, agent]));
    const datasetMap = new Map(
      datasets.map((dataset: any) => [dataset.id, dataset])
    );

    // First, filter completed evaluations and create a map to find the most recent for each agent-dataset combination
    const completedEvaluations = evaluations.filter(
      (evaluation: EvaluationRun) =>
        evaluation.status === "completed" &&
        evaluation.completed_tests > 0 &&
        agentMap.has(evaluation.agent_id)
    );

    // Group by agent_id + dataset_id and keep only the most recent
    const latestEvaluationsMap = new Map<string, EvaluationRun>();

    completedEvaluations.forEach((evaluation: EvaluationRun) => {
      const key = `${evaluation.agent_id}_${evaluation.dataset_id}`;
      const existing = latestEvaluationsMap.get(key);

      if (
        !existing ||
        new Date(evaluation.created_at) > new Date(existing.created_at)
      ) {
        latestEvaluationsMap.set(key, evaluation);
      }
    });

    const entries = Array.from(latestEvaluationsMap.values())
      .map((evaluation: EvaluationRun) => {
        const agent = agentMap.get(evaluation.agent_id);
        const dataset = datasetMap.get(evaluation.dataset_id);
        const passRate =
          (evaluation.passed_count / evaluation.completed_tests) * 100;

        return {
          evaluation: evaluation,
          agent: agent,
          dataset: dataset,
          passRate: passRate,
          passRateDisplay: `${Math.round(passRate)}%`,
          datasetName:
            dataset?.seed?.name || dataset?.name || evaluation.dataset_id,
          model: agent?.model || "Unknown",
        };
      })
      .sort((a, b) => b.passRate - a.passRate); // Sort by pass rate descending

    // Extract unique values for filters
    const uniqueDatasets = Array.from(
      new Set(entries.map((entry) => entry.datasetName))
    ).sort();
    const uniqueModels = Array.from(
      new Set(entries.map((entry) => entry.model))
    ).sort();

    return { entries, datasets: uniqueDatasets, models: uniqueModels };
  }, [evaluations, agents, datasets]);

  // Apply filters and search using useTableState
  const {
    searchTerm,
    setSearchTerm,
    sortOrder,
    handleSort,
    filteredData: filteredEntries,
  } = useTableState({
    data: processedData.entries,
    searchFields: ["agent.name"],
    defaultSortField: "passRate",
    filters: {
      dataset: {
        getValue: (entry: any) => entry.datasetName,
        selectedValues: selectedDatasetFilters,
      },
      model: {
        getValue: (entry: any) => entry.model,
        selectedValues: selectedModelFilters,
      },
    },
  });

  const loading = evaluationsLoading || agentsLoading || datasetsLoading;
  const error = evaluationsError || agentsError || datasetsError;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <CircleNotch size={48} className="animate-spin text-primary mb-4" />
        <p className="text-muted-foreground">Loading results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leaderboard</h1>
          <p className="text-muted-foreground mt-1">
            Compare agent performance across evaluation datasets
          </p>
        </div>
        <NoDataCard
          icon={<Trophy size={48} className="text-muted-foreground mb-4" />}
          title="Failed to load evaluation data"
          description={`Please try again later. ${error}`}
        />
      </div>
    );
  }

  const handleRowClick = (entry: any) => {
    if (entry.agent?.id) {
      navigate(`/agents/${entry.agent.id}`);
    }
  };

  const columns: TableColumn[] = [
    {
      key: "agentName",
      header: "Agent name",
      width: "40%",
      minWidth: "200px",
      render: (entry: any) => (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            paddingRight: "10.7%",
            boxSizing: "border-box",
          }}
        >
          <img
            src={getAgentIcon(entry.agent.id)}
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
            }}
          >
            <div style={{ fontWeight: 600, fontSize: "14px" }}>
              {entry.agent?.name || "Unknown Agent"}
            </div>
            <div style={{ fontSize: "12px", color: "#6b7280" }}>
              {entry.agent?.description || "No description"}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: "dataset",
      header: "Evaluation dataset",
      width: "30%",
      minWidth: "180px",
      render: (entry: any) => entry.datasetName,
    },
    {
      key: "model",
      header: "Model",
      width: "20%",
      minWidth: "120px",
      render: (entry: any) => (
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
          {entry.model}
        </Badge>
      ),
    },
    {
      key: "score",
      header: "Score",
      width: "10%",
      minWidth: "80px",
      render: (entry: any) => {
        return (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ScoreBadge score={entry.passRate} />
          </div>
        );
      },
    },
  ];

  const filters: FilterOption[] = [
    {
      key: "dataset",
      placeholder: "Evaluation dataset",
      options: processedData.datasets,
      selectedOptions: selectedDatasetFilters,
      onSelectionChange: setSelectedDatasetFilters,
      multiselect: true,
      minWidth: "200px",
    },
    {
      key: "model",
      placeholder: "Model type",
      options: processedData.models,
      selectedOptions: selectedModelFilters,
      onSelectionChange: setSelectedModelFilters,
      multiselect: true,
      minWidth: "180px",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Leaderboard</h1>
        <p className="text-muted-foreground mt-1">
          Compare agent performance across evaluation datasets
        </p>
      </div>

      {processedData.entries.length === 0 ? (
        <NoDataCard
          icon={<Trophy size={48} className="text-muted-foreground mb-4" />}
          title="No evaluation data available yet"
          description="Run some evaluations to see leaderboard results"
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
            data={filteredEntries}
            onRowClick={handleRowClick}
            emptyState={
              <NoDataCard
                icon={
                  <Trophy size={48} className="text-muted-foreground mb-4" />
                }
                title={`No agents found matching "${searchTerm}"`}
                description="Try adjusting your search terms or filters"
              />
            }
          />
        </>
      )}
    </div>
  );
}
