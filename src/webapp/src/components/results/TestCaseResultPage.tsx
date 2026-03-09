import { useParams, useNavigate } from "react-router-dom";
import { useState, useMemo, useEffect } from "react";
import { useEvaluation } from "@/hooks/useEvaluation";
import { useDatasets } from "@/hooks/useDatasets";
import { useAgents } from "@/hooks/useAgents";
import { useTestCase } from "@/hooks/useTestCase";
import { TestCaseResult } from "@/lib/api";
import { formatJsonForDisplay, formatResponseJson, isResponseLong, getTruncatedResponse } from "@/lib/jsonUtils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeft20Regular,
  SpinnerIos20Regular,
  Checkmark20Regular,
  Dismiss20Regular,
  Chat20Regular,
  Document20Regular,
  ArrowMinimize20Regular,
  ArrowMaximize20Regular,
  Warning20Regular,
  Wrench20Regular,
  ClipboardCheckmark20Regular,
  ChartMultiple20Regular,
} from "@fluentui/react-icons";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, XCircle } from "@phosphor-icons/react";

import { Separator } from "@/components/ui/separator";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import { NoDataCard } from "@/components/shared/NoDataCard";
import { AIContentDisclaimer } from "@/components/shared/AIContentDisclaimer";
import { useRubricsConfig } from "@/hooks/useRubricsConfig";
import { useSelectableClick } from "@/hooks/useSelectableClick";
import { getKeyboardProps } from "@/hooks/useKeyboardClick";

interface BaseCardItem {
  id: string;
  type:
    | "tools"
    | "assertions"
    | "response"
    | "description"
    | "input"
    | "expected_response"
    | "quality"
    | "error"
    | "rubric";
  title: string;
  content: string;
}

interface ToolCardItem extends BaseCardItem {
  type: "tools";
  actualTools: any[];
  expectedTools: any[];
}

interface AssertionCardItem extends BaseCardItem {
  type: "assertions";
  toolExpectations: any[];
}

interface BasicInfoCardItem extends BaseCardItem {
  type:
    | "response"
    | "description"
    | "input"
    | "expected_response"
    | "quality"
    | "error";
}

interface RubricCardItem extends BaseCardItem {
  type: "rubric";
}

type CardItem =
  | ToolCardItem
  | AssertionCardItem
  | BasicInfoCardItem
  | RubricCardItem;

const useBreadcrumbStyles = makeStyles({
  // Remove custom styles since we're using Fluent UI's built-in truncation
});

export function TestCaseResultPage() {
  const { eval_id, testcase_id } = useParams<{
    eval_id: string;
    testcase_id: string;
  }>();
  const navigate = useNavigate();
  const breadcrumbStyles = useBreadcrumbStyles();
  const { evaluation, loading, error } = useEvaluation(eval_id);
  const { datasets } = useDatasets();
  const { agents } = useAgents();
  const [collapsedCards, setCollapsedCards] = useState<Set<string>>(new Set());
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [expandedResponses, setExpandedResponses] = useState<Set<string>>(new Set());
  const rubricsConfig = useRubricsConfig();
  const { createClickHandler } = useSelectableClick();

  // Initialize all cards as collapsed
  const [initializedCollapsed, setInitializedCollapsed] = useState(false);

  // Get the dataset_id from evaluation to fetch the test case
  const datasetId = evaluation?.dataset_id;
  const { testCase: fetchedTestCase, loading: testCaseLoading } = useTestCase(
    datasetId,
    testcase_id
  );

  const { testCaseResult, agent, dataset } = useMemo(() => {
    if (!evaluation || !testcase_id) {
      return { testCaseResult: null, agent: null, dataset: null };
    }

    // Find the test case result in the evaluation
    // Try both exact match and decoded match in case of URL encoding issues
    let foundTestCaseResult = evaluation.test_cases?.find(
      (tc) => tc.testcase_id === testcase_id
    );

    // If not found, try with decoded testcase_id
    if (!foundTestCaseResult && testcase_id) {
      const decodedTestcaseId = decodeURIComponent(testcase_id);
      foundTestCaseResult = evaluation.test_cases?.find(
        (tc) => tc.testcase_id === decodedTestcaseId
      );
    }

    // If still not found, try case-insensitive comparison
    if (!foundTestCaseResult && testcase_id) {
      foundTestCaseResult = evaluation.test_cases?.find(
        (tc) => tc.testcase_id.toLowerCase() === testcase_id.toLowerCase()
      );
    }

    if (!foundTestCaseResult) {
      return { testCaseResult: null, agent: null, dataset: null };
    }

    // Find the dataset
    const foundDataset = datasets.find((s) => s.id === evaluation.dataset_id);

    // Find the agent
    const foundAgent = agents.find((a) => a.id === evaluation.agent_id);

    return {
      testCaseResult: foundTestCaseResult,
      agent: foundAgent,
      dataset: foundDataset,
    };
  }, [evaluation, testcase_id, datasets, agents]);

  // Use the fetched test case instead of the one from datasets
  const testCase = fetchedTestCase;

  const cardData = useMemo(() => {
    if (!testCaseResult) return [];

    const items: CardItem[] = [];

    // Add actual tool calls card
    if (
      testCaseResult.actual_tool_calls &&
      testCaseResult.actual_tool_calls.length > 0
    ) {
      items.push({
        id: "actual_tools",
        type: "tools",
        title: "Actual Tool Calls",
        content: `${testCaseResult.actual_tool_calls.length} tool call${
          testCaseResult.actual_tool_calls.length !== 1 ? "s" : ""
        }`,
        actualTools: testCaseResult.actual_tool_calls,
        expectedTools: [],
      });
    }

    // Add cards for each expected tool with assertions
    if (testCaseResult.tool_expectations?.length) {
      testCaseResult.tool_expectations.forEach((toolExp, index) => {
        items.push({
          id: `tool_expectation_${index}`,
          type: "assertions",
          title: `Expected Tool: ${toolExp.name_of_tool}`,
          content: `${toolExp.arguments?.length || 0} argument${
            toolExp.arguments?.length !== 1 ? "s" : ""
          } with assertions`,
          toolExpectations: [toolExp], // Single tool expectation per card
        });
      });
    }

    // Add cards for expected tools that weren't called (and don't have tool_expectations)
    if (testCaseResult.expected_tools?.length) {
      testCaseResult.expected_tools.forEach((expectedTool, index) => {
        // Only add if this tool doesn't already have a tool_expectation card
        const hasToolExpectation = testCaseResult.tool_expectations?.some(
          (toolExp) => toolExp.name_of_tool === expectedTool.name_of_tool
        );

        if (!hasToolExpectation) {
          items.push({
            id: `expected_tool_${index}`,
            type: "assertions",
            title: `Expected Tool: ${expectedTool.name_of_tool}`,
            content: expectedTool.was_called
              ? "Tool was called"
              : "Tool was not called",
            toolExpectations: [
              {
                name_of_tool: expectedTool.name_of_tool,
                arguments: [], // No arguments for this case
              },
            ],
          });
        }
      });
    }

    // Add response quality assessment card
    if (testCaseResult.response_quality_assertion) {
      items.push({
        id: "response_quality",
        type: "quality",
        title: "Response Quality Assessment",
        content: testCaseResult.response_quality_assertion.llm_judge_output,
      });
    }

    // Add cards for response quality rubrics (if available from test case and enabled)
    if (
      rubricsConfig.enabled &&
      testCase?.response_quality_expectation?.rubrics?.length
    ) {
      testCase.response_quality_expectation.rubrics.forEach((rubric, index) => {
        items.push({
          id: `rubric_${index}`,
          type: "rubric",
          title: `Response Quality Rubric: ${rubric.name}`,
          content: `Threshold: ${(rubric.threshold * 100).toFixed(0)}%`,
        });
      });
    }

    // Add execution error if present
    if (testCaseResult.execution_error) {
      items.push({
        id: "error",
        type: "error",
        title: "Execution Error",
        content: testCaseResult.execution_error,
      });
    }

    return items;
  }, [testCaseResult, testCase, rubricsConfig.enabled]);

  // Initialize all cards as collapsed when cardData changes
  useEffect(() => {
    if (cardData.length > 0 && !initializedCollapsed) {
      const allCardIds = new Set(cardData.map((item) => item.id));
      setCollapsedCards(allCardIds);
      setInitializedCollapsed(true);
    }
  }, [cardData, initializedCollapsed]);

  const [activeFilter, setActiveFilter] = useState<string>("All");

  // Helper function to determine if a card passed or failed
  const getCardStatus = (item: CardItem) => {
    switch (item.type) {
      case "assertions": {
        const assertionItem = item as AssertionCardItem;
        const toolExp = assertionItem.toolExpectations[0];

        // First check if the tool was actually called
        const actualToolCall = testCaseResult?.actual_tool_calls?.find(
          (call) => call.name === toolExp.name_of_tool
        );

        // If tool wasn't called, it's a failure
        if (!actualToolCall) {
          return "Failed";
        }

        // If tool was called but has no arguments to check, it's a pass
        if (!toolExp.arguments || toolExp.arguments.length === 0) {
          return "Passed";
        }

        // If tool was called and has arguments, check all assertions
        const allAssertions = toolExp.arguments.flatMap(
          (arg: any) => arg.assertions
        );
        const allPassed = allAssertions.every(
          (assertion: any) => assertion.passed
        );
        return allPassed ? "Passed" : "Failed";
      }
      case "quality":
        return testCaseResult?.response_quality_assertion?.passed
          ? "Passed"
          : "Failed";
      case "tools":
      case "description":
      case "input":
      case "expected_response":
      case "rubric":
      case "error":
      default:
        return null; // No pass/fail status
    }
  };

  const getCardIcon = (type: string, item?: CardItem) => {
    switch (type) {
      case "tools":
        return <Wrench20Regular className="text-primary" />;
      case "assertions":
        return <Document20Regular className="text-primary" />;
      case "quality":
        return testCaseResult?.response_quality_assertion?.passed ? (
          <Checkmark20Regular style={{ color: "#0D7717" }} />
        ) : (
          <Dismiss20Regular style={{ color: "#C4314B" }} />
        );
      case "rubric":
        return <ChartMultiple20Regular className="text-primary" />;
      case "error":
        return <Warning20Regular style={{ color: "#C4314B" }} />;
      default:
        return null;
    }
  };

  const toggleCardCollapse = (cardId: string) => {
    setCollapsedCards((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(cardId)) {
        newSet.delete(cardId);
      } else {
        newSet.add(cardId);
      }
      return newSet;
    });
  };

  const handleCardToggle = createClickHandler((cardId: string) => {
    toggleCardCollapse(cardId);
  });

  // Simple filtering logic
  const filteredCardData = useMemo(() => {
    if (activeFilter === "All") {
      return cardData;
    }

    return cardData.filter((item) => {
      switch (activeFilter) {
        case "Expected Tool Calls":
          return item.type === "assertions";
        case "Response Quality Assertions":
          return item.type === "quality";
        case "Actual Tool Calls":
          return item.type === "tools";
        default:
          return true;
      }
    });
  }, [cardData, activeFilter]);

  const toggleExpanded = (itemId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const toggleResponseExpanded = (responseId: string) => {
    setExpandedResponses((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(responseId)) {
        newSet.delete(responseId);
      } else {
        newSet.add(responseId);
      }
      return newSet;
    });
  };

  const renderCardContent = (item: CardItem) => {
    const isExpanded = expandedItems.has(item.id);
    const maxItemsToShow = 2;

    if (item.type === "tools") {
      const toolItem = item as ToolCardItem;
      return (
        <div className="space-y-3">
          {/* Show only Actual Tool Calls */}
          {toolItem.actualTools.length > 0 && (
            <>
              <div className="text-sm bg-muted/50 p-3 rounded-md space-y-4">
                <p className="text-sm text-muted-foreground">Tool calls</p>
                {(isExpanded
                  ? toolItem.actualTools
                  : toolItem.actualTools.slice(0, maxItemsToShow)
                ).map((toolCall, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">
                        {toolCall.name}
                      </code>
                    </div>
                    <div className="space-y-1">
                      {toolCall.arguments && toolCall.arguments.length > 0 ? (
                        toolCall.arguments.map((arg: any, argIdx: number) => (
                          <div key={argIdx} className="text-xs">
                            <span className="font-semibold text-blue-700">
                              {arg.name}:
                            </span>{" "}
                            <span className="font-mono">
                              {formatJsonForDisplay(arg.value)}
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground italic">
                          No parameters
                        </p>
                      )}
                    </div>
                    {/* Show MCP tool response */}
                    {toolCall.response && (
                      <div className="mt-2">
                        <div className="text-xs">
                          <span className="text-muted-foreground font-medium">
                            Tool response:
                          </span>{" "}
                          <span className={`text-xs rounded ${
                            toolCall.response?.success === true 
                              ? 'font-medium' 
                              : 'bg-red-100 text-red-800 px-2 py-1'
                          }`}
                            style={toolCall.response?.success === true ? {
                              background: "#F1FAF1",
                              color: "#0D7717",
                              borderRadius: "4px",
                              padding: "2px 4px",
                              fontWeight: "500"
                            } : undefined}
                          >
                            {toolCall.response?.success === true ? 'Success' : 'Failed'}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {toolItem.actualTools.length > maxItemsToShow && (
                  <div className="flex justify-center pt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpanded(item.id);
                      }}
                    >
                      {isExpanded
                        ? "Show Less"
                        : `Show More (${
                            toolItem.actualTools.length - maxItemsToShow
                          })`}
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      );
    } else if (item.type === "assertions") {
      const assertionItem = item as AssertionCardItem;
      // Since we're showing one tool per card, just get the first (and only) tool
      const toolExp = assertionItem.toolExpectations[0];

      // Find the actual tool call that matches this expected tool
      const actualToolCall = testCaseResult?.actual_tool_calls?.find(
        (call) => call.name === toolExp.name_of_tool
      );
      // Find the toolCallExpectation from the original dataset
      const toolCallExpectation = testCase?.tool_expectations?.find(
        (te) => te.name === toolExp.name_of_tool
      );

      return (
        <div className="space-y-3">
          <div className="text-sm bg-muted/50 p-3 rounded-md space-y-4">
            {/* Show tool call status first */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Tool status</p>
              <div className="flex items-center justify-between p-2 rounded border bg-card">
                {actualToolCall ? (
                  <>
                    <div className="flex items-center gap-2">
                      <CheckCircle
                        size={16}
                        style={{ color: "#0D7717" }}
                        weight="fill"
                      />
                      <span className="text-sm font-mono">
                        {toolExp.name_of_tool}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        was called
                      </span>
                    </div>
                    <Badge
                      variant="default"
                      className="text-xs"
                      style={{
                        background: "#F1FAF1",
                        color: "#0D7717",
                        borderRadius: "4px",
                        padding: "2px 4px",
                      }}
                    >
                      Called
                    </Badge>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <XCircle
                        size={16}
                        style={{ color: "#C4314B" }}
                        weight="fill"
                      />
                      <span className="text-sm font-mono">
                        {toolExp.name_of_tool}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        was not called
                      </span>
                    </div>
                    <Badge
                      variant="destructive"
                      className="text-xs"
                      style={{
                        background: "#FDF6F6",
                        color: "#C4314B",
                        borderRadius: "4px",
                        padding: "2px 4px",
                      }}
                    >
                      Not Called
                    </Badge>
                  </>
                )}
              </div>
            </div>

            {/* Show tool response if available */}
            {actualToolCall && actualToolCall.response && (
              <div className="space-y-2">
                {(() => {
                  const responseId = `${item.id}-assertion-response`;
                  const isResponseExpanded = expandedResponses.has(responseId);
                  const isSuccess = actualToolCall.response.success === true;
                  
                  return (
                    <>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <p className="text-sm text-muted-foreground">Tool response</p>
                          <span className={`text-xs rounded ${
                            isSuccess 
                              ? 'font-medium' 
                              : 'bg-red-100 text-red-800 px-2 py-1'
                          }`}
                            style={isSuccess ? {
                              background: "#F1FAF1",
                              color: "#0D7717",
                              borderRadius: "4px",
                              padding: "2px 4px",
                              fontWeight: "500"
                            } : undefined}
                          >
                            {isSuccess ? 'Success' : 'Failed'}
                          </span>
                          {!isResponseExpanded && (
                            <span 
                              className="text-xs text-muted-foreground italic cursor-pointer hover:text-foreground transition-colors"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleResponseExpanded(responseId);
                              }}
                            >
                              Click to view details
                            </span>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleResponseExpanded(responseId);
                          }}
                          className="text-muted-foreground hover:text-foreground transition-colors"
                        >
                          {isResponseExpanded ? (
                            <ArrowMinimize20Regular style={{ fontSize: "14px" }} />
                          ) : (
                            <ArrowMaximize20Regular style={{ fontSize: "14px" }} />
                          )}
                        </button>
                      </div>
                      {isResponseExpanded && (
                        <>
                          {isSuccess ? (
                            <pre className="text-xs font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed bg-green-50 p-3 rounded border">
                              {formatResponseJson(actualToolCall.response)}
                            </pre>
                          ) : (
                            <div className="text-xs text-red-800 bg-red-50 p-3 rounded">
                              <div className="font-medium mb-1">Error:</div>
                              <div className="font-mono">
                                {actualToolCall.response.error || actualToolCall.response.message || 'Unknown error'}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </>
                  );
                })()}
              </div>
            )}

            {/* Show arguments and assertions if available */}
            {actualToolCall &&
            toolExp.arguments &&
            toolExp.arguments.length > 0 ? (
              <>
                <p className="text-sm text-muted-foreground">
                  Tool arguments with assertions
                </p>
                {(isExpanded
                  ? toolExp.arguments
                  : toolExp.arguments.slice(0, maxItemsToShow)
                ).map((arg: any, argIdx: number) => {
                  // Find the actual argument value
                  const actualArg = actualToolCall?.arguments?.find(
                    (actualArg) => actualArg.name === arg.name_of_argument
                  );

                  //Find the list of assertions from toolCallExpectation for this argument
                  const toolCallExpectationAssertions =
                    toolCallExpectation?.arguments?.find(
                      (a) => a.name === arg.name_of_argument
                    )?.assertion || [];

                  return (
                    <div key={argIdx} className="space-y-2">
                      <div className="flex items-center gap-2">
                        <code className="text-xs font-mono bg-primary/10 px-1.5 py-0.5 rounded">
                          {arg.name_of_argument}
                        </code>
                      </div>

                      {/* Show actual argument value */}
                      {actualArg && (
                        <div className="space-y-1">
                          <div className="text-xs font-medium text-muted-foreground">
                            Actual Value:
                          </div>
                          <pre className="text-xs font-mono whitespace-pre-wrap text-muted-foreground">
                            {formatJsonForDisplay(actualArg.value)}
                          </pre>
                        </div>
                      )}

                      {/* Show assertions */}
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                          <ClipboardCheckmark20Regular
                            style={{ fontSize: "12px" }}
                          />
                          Assertions ({arg.assertions.length})
                        </div>
                        {arg.assertions.map(
                          (assertion: any, assertIdx: number) => {
                            // Get the corresponding assertion text from toolCallExpectationAssertions
                            const correspondingAssertion =
                              toolCallExpectationAssertions[assertIdx] ||
                              toolCallExpectationAssertions[0];

                            return (
                              <div
                                key={assertIdx}
                                className="flex items-start gap-2 mb-6"
                              >
                                {assertion.passed ? (
                                  <Checkmark20Regular
                                    style={{
                                      color: "#0D7717",
                                      fontSize: "12px",
                                    }}
                                    className="mt-0.5 flex-shrink-0"
                                  />
                                ) : (
                                  <Dismiss20Regular
                                    style={{
                                      color: "#C4314B",
                                      fontSize: "12px",
                                    }}
                                    className="mt-0.5 flex-shrink-0"
                                  />
                                )}
                                <div className="flex-1">
                                  <div className="text-xs font-medium mb-1">
                                    {assertion.passed ? "PASSED" : "FAILED"}
                                  </div>
                                  <p className="text-xs text-muted-foreground mb-2">
                                    <span className="font-semibold">
                                      Assertion:
                                    </span>{" "}
                                    {correspondingAssertion ||
                                      "No assertion text available"}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    <span className="font-semibold">
                                      LLM Judge Response:
                                    </span>{" "}
                                    {assertion.llm_judge_output}
                                  </p>
                                </div>
                              </div>
                            );
                          }
                        )}
                      </div>
                    </div>
                  );
                })}
                {toolExp.arguments.length > maxItemsToShow && (
                  <div className="flex justify-center pt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpanded(item.id);
                      }}
                    >
                      {isExpanded
                        ? "Show Less"
                        : `Show More (${
                            toolExp.arguments.length - maxItemsToShow
                          })`}
                    </Button>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No arguments to evaluate
              </p>
            )}
          </div>
        </div>
      );
    } else if (item.type === "quality") {
      // Response Quality with pass/fail and LLM explanation
      const passed = testCaseResult?.response_quality_assertion?.passed;
      const originalAssertion =
        testCase?.response_quality_expectation?.assertion;

      return (
        <div className="space-y-3">
          {/* Show original assertion if available */}
          {originalAssertion && (
            <div className="bg-muted/50 p-3 rounded">
              <div className="text-sm font-medium text-muted-foreground mb-2">
                Original Assertion:
              </div>
              <p className="text-sm whitespace-pre-wrap">{originalAssertion}</p>
            </div>
          )}

          {/* Show evaluation result */}
          <div
            className="border-l-4 pl-3 py-2 rounded"
            style={{
              backgroundColor: passed ? "#F1FAF1" : "#FDF6F6",
              borderLeftColor: passed ? "#0D7717" : "#C4314B",
            }}
          >
            <div className="flex items-start gap-2">
              {passed ? (
                <Checkmark20Regular
                  style={{ color: "#0D7717", fontSize: "14px" }}
                  className="mt-0.5 flex-shrink-0"
                />
              ) : (
                <Dismiss20Regular
                  style={{ color: "#C4314B", fontSize: "14px" }}
                  className="mt-0.5 flex-shrink-0"
                />
              )}
              <div className="flex-1">
                <div className="text-sm font-medium mb-2">
                  {passed ? "PASSED" : "FAILED"}
                </div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  LLM Judge Response:
                </div>
                <p className="text-sm whitespace-pre-wrap text-muted-foreground">
                  {item.content}
                </p>
              </div>
            </div>
          </div>
        </div>
      );
    } else if (item.type === "rubric") {
      // Rubric information
      return (
        <div className="space-y-2">
          <div className="text-sm bg-muted/50 p-3 rounded-md">
            {item.content}
          </div>
        </div>
      );
    } else {
      // Basic info cards
      return (
        <div className="space-y-2">
          <div className="text-sm bg-muted/50 p-3 rounded-md whitespace-pre-wrap max-h-[200px] overflow-y-auto">
            {item.content}
          </div>
        </div>
      );
    }
  };

  if (loading || testCaseLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <SpinnerIos20Regular
          className="animate-spin text-primary mb-4"
          style={{ fontSize: "48px" }}
        />
        <p className="text-muted-foreground">Loading test case result...</p>
        {eval_id && (
          <p className="text-sm text-muted-foreground mt-2">
            Evaluation ID: {eval_id} | Test Case ID: {testcase_id}
          </p>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
        <Alert variant="destructive" className="max-w-md mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button
          onClick={() => navigate("/agents")}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft20Regular />
          Back to Agents
        </Button>
      </div>
    );
  }

  if (!evaluation || !testCaseResult) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h2 className="text-2xl font-bold mb-2">Test case result not found</h2>
        <p className="text-muted-foreground mb-6">
          {!evaluation
            ? "The evaluation could not be loaded."
            : "The test case result you're looking for doesn't exist in this evaluation."}
        </p>
        {evaluation && (
          <div className="text-sm text-muted-foreground mb-4 space-y-1">
            <p>
              <strong>Evaluation ID:</strong> {eval_id}
            </p>
            <p>
              <strong>Looking for Test Case ID:</strong> {testcase_id}
            </p>
            <p>
              <strong>Evaluation Status:</strong> {evaluation.status}
            </p>
            <p>
              <strong>Total Test Cases:</strong>{" "}
              {evaluation.test_cases?.length || 0}
            </p>
            {evaluation.test_cases?.length > 0 && (
              <div>
                <p>
                  <strong>Available Test Case IDs:</strong>
                </p>
                <ul className="list-disc list-inside ml-2">
                  {evaluation.test_cases.map((tc, idx) => (
                    <li key={idx} className="font-mono text-xs">
                      {tc.testcase_id}
                      {tc.testcase_id === testcase_id && (
                        <span style={{ color: "#0D7717" }}>
                          {" "}
                          ← Exact match!
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <Button
            onClick={() => navigate(`/evaluations/${eval_id}`)}
            variant="outline"
            className="gap-2"
          >
            <ArrowLeft20Regular />
            Back to Evaluation
          </Button>
          <Button
            onClick={() => navigate("/agents")}
            variant="ghost"
            className="gap-2"
          >
            <ArrowLeft20Regular />
            All Agents
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <Breadcrumb aria-label="Test case result navigation" className="mb-4">
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
                agent?.name || "Unknown Agent",
                30
              ) ? (
                <Tooltip
                  withArrow
                  content={agent?.name || "Unknown Agent"}
                  relationship="label"
                >
                  <BreadcrumbButton
                    onClick={() => navigate(`/agents/${agent?.id}`)}
                  >
                    {truncateBreadcrumbLongName(agent?.name || "Unknown Agent")}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton
                  onClick={() => navigate(`/agents/${agent?.id}`)}
                >
                  {agent?.name}
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
            <BreadcrumbDivider />
            <BreadcrumbItem>
              {isTruncatableBreadcrumbContent(evaluation.name, 30) ? (
                <Tooltip
                  withArrow
                  content={evaluation.name}
                  relationship="label"
                >
                  <BreadcrumbButton
                    onClick={() => navigate(`/evaluations/${eval_id}`)}
                  >
                    {truncateBreadcrumbLongName(evaluation.name)}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton
                  onClick={() => navigate(`/evaluations/${eval_id}`)}
                >
                  {evaluation.name}
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
            <BreadcrumbDivider />
            <BreadcrumbItem>
              {isTruncatableBreadcrumbContent(
                testCase?.name || `Test Case: ${testcase_id}`,
                30
              ) ? (
                <Tooltip
                  withArrow
                  content={testCase?.name || `Test Case: ${testcase_id}`}
                  relationship="label"
                >
                  <BreadcrumbButton current>
                    {truncateBreadcrumbLongName(
                      testCase?.name || `Test Case: ${testcase_id}`
                    )}
                  </BreadcrumbButton>
                </Tooltip>
              ) : (
                <BreadcrumbButton current>
                  {testCase?.name || `Test Case: ${testcase_id}`}
                </BreadcrumbButton>
              )}
            </BreadcrumbItem>
          </Breadcrumb>
          <h1 className="text-3xl font-bold tracking-tight">
            {testCase?.name || `Test Case: ${testcase_id}`}
          </h1>
          <p className="text-muted-foreground text-sm">
            {testCase?.description || "No description available"}
          </p>
          <AIContentDisclaimer />
        </div>
        <Badge
          variant={testCaseResult.passed ? "default" : "destructive"}
          className="text-lg px-4 py-2"
          style={{
            backgroundColor: testCaseResult.passed ? "#F1FAF1" : "#FDF6F6",
            color: testCaseResult.passed ? "#0D7717" : "#C4314B",
            borderRadius: "4px",
          }}
        >
          {testCaseResult.passed ? "Passed" : "Failed"}
        </Badge>
      </div>

      {/* Summary Statistics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tool calls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-indigo-500">
              {testCaseResult.actual_tool_calls?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Actual</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Expected tools called
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-indigo-500">
              {testCaseResult.expected_tools?.filter((t) => t.was_called)
                .length || 0}
              /{testCaseResult.expected_tools?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Called</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Failed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-indigo-500">
              {(() => {
                let failedCount = 0;
                // Count failed tool expectations
                testCaseResult.tool_expectations?.forEach((toolExp) => {
                  toolExp.arguments.forEach((arg: any) => {
                    arg.assertions.forEach((assertion: any) => {
                      if (!assertion.passed) failedCount++;
                    });
                  });
                });
                // Count failed response quality
                if (
                  testCaseResult.response_quality_assertion &&
                  !testCaseResult.response_quality_assertion.passed
                ) {
                  failedCount++;
                }
                // Count uncalled expected tools
                testCaseResult.expected_tools?.forEach((tool) => {
                  if (!tool.was_called) failedCount++;
                });
                return failedCount;
              })()}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Assertion failed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Execution Error Alert */}
      {testCaseResult.execution_error && (
        <Alert
          style={{
            borderColor: "#C4314B",
            backgroundColor: "#FDF6F6",
          }}
        >
          <Warning20Regular style={{ color: "#C4314B" }} />
          <AlertDescription style={{ color: "#C4314B" }}>
            <strong>Execution Error:</strong> {testCaseResult.execution_error}
          </AlertDescription>
        </Alert>
      )}

      {/* Input and Response Section */}
      <div className="grid gap-4 md:grid-cols-2 md:grid-rows-1">
        <Card className="flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Chat20Regular />
              Input (Agent Prompt)
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            <div className="text-sm bg-gray-50 p-4 rounded-md whitespace-pre-wrap flex-1 overflow-y-auto border min-h-[120px] max-h-[300px]">
              {testCase?.input || "No input available"}
            </div>
          </CardContent>
        </Card>

        <Card className="flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Chat20Regular />
              Response
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            <div className="text-sm bg-gray-50 p-4 rounded-md whitespace-pre-wrap flex-1 overflow-y-auto border min-h-[120px] max-h-[300px]">
              {testCaseResult.response_from_agent || "No response available"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Section */}
      <div className="space-y-4">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Results</h2>

          {/* Simple pill filters */}
          <div className="flex items-center gap-2">
            {[
              "All",
              "Actual Tool Calls",
              "Expected Tool Calls",
              "Response Quality Assertions",
            ].map((filter) => (
              <Button
                key={filter}
                variant={activeFilter === filter ? "default" : "outline"}
                size="sm"
                onClick={() => setActiveFilter(filter)}
                className={`rounded-full px-4 py-2 text-sm ${
                  activeFilter === filter
                    ? "bg-indigo-50 text-indigo-600 border-indigo-100 hover:bg-indigo-100"
                    : "border-gray-300 text-gray-700 hover:bg-gray-50"
                }`}
              >
                {filter}
              </Button>
            ))}
          </div>
        </div>

        {cardData.length === 0 ? (
          <NoDataCard
            icon={
              <Document20Regular
                className="text-muted-foreground mb-4"
                style={{ fontSize: "48px" }}
              />
            }
            title="No detailed information available"
            description="This test case has no additional details."
          />
        ) : (
          <>
            <div className="space-y-3">
              {filteredCardData.map((item) => {
                const isCollapsed = collapsedCards.has(item.id);
                const status = getCardStatus(item);
                const keyboardProps = getKeyboardProps((event) => handleCardToggle(item.id, event));
                return (
                  <Card
                    key={item.id}
                    className="transition-all cursor-pointer border-indigo-100/70 shadow-indigo-50/30 shadow-sm hover:shadow-indigo-100/50 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                    {...keyboardProps}
                    style={{ userSelect: "text" }}
                  >
                    {isCollapsed ? (
                      // Collapsed view - compact single line like screenshot
                      <div className="flex items-center justify-between gap-4 p-4">
                        <div className="flex items-center gap-3">
                          {getCardIcon(item.type)}
                          <span className="text-sm font-medium">
                            {item.type === "tools" && "Actual Tool Calls"}
                            {item.type === "assertions" &&
                              (item as AssertionCardItem).toolExpectations[0]
                                ?.name_of_tool}
                            {item.type === "quality" && "Response Quality"}
                            {item.type === "rubric" && "Rubric"}
                            {item.type === "error" && "Error"}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {item.type === "tools" &&
                              (item as ToolCardItem).actualTools &&
                              `${
                                (item as ToolCardItem).actualTools.length
                              } calls`}
                            {item.type === "assertions" && "Tool Check"}
                            {item.type === "quality" && "Quality Check"}
                            {item.type === "rubric" && "Rubric Check"}
                            {item.type === "error" && "Error"}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {/* Add PASSED/FAILED badge for items with status */}
                          {status && (
                            <Badge
                              variant={
                                status === "Passed" ? "default" : "destructive"
                              }
                              className="text-xs"
                              style={{
                                backgroundColor:
                                  status === "Passed" ? "#F1FAF1" : "#FDF6F6",
                                color:
                                  status === "Passed" ? "#0D7717" : "#C4314B",
                                borderRadius: "4px",
                                padding: "2px 4px",
                              }}
                            >
                              {status === "Passed" ? "Passed" : "Failed"}
                            </Badge>
                          )}
                          <ArrowMaximize20Regular
                            className="text-muted-foreground"
                            style={{ fontSize: "14px" }}
                          />
                        </div>
                      </div>
                    ) : (
                      // Expanded view - full card
                      <>
                        <CardHeader className="pb-1">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                {getCardIcon(item.type)}
                                <CardTitle className="text-lg">
                                  {item.title}
                                </CardTitle>
                              </div>
                              {item.type === "tools" &&
                                (item as ToolCardItem).actualTools && (
                                  <CardDescription className="mt-1">
                                    {(item as ToolCardItem).actualTools.length}{" "}
                                    tool call
                                    {(item as ToolCardItem).actualTools
                                      .length !== 1
                                      ? "s"
                                      : ""}
                                  </CardDescription>
                                )}
                              {item.type === "assertions" &&
                                (item as AssertionCardItem)
                                  .toolExpectations && (
                                  <CardDescription className="mt-1">
                                    {(item as AssertionCardItem)
                                      .toolExpectations[0]?.arguments?.length ||
                                      0}{" "}
                                    argument
                                    {(item as AssertionCardItem)
                                      .toolExpectations[0]?.arguments
                                      ?.length !== 1
                                      ? "s"
                                      : ""}{" "}
                                    with assertions
                                  </CardDescription>
                                )}
                              {item.type === "quality" && (
                                <CardDescription className="mt-1">
                                  Quality assessment evaluation
                                </CardDescription>
                              )}
                              {item.type === "rubric" && (
                                <CardDescription className="mt-1">
                                  Quality evaluation rubric
                                </CardDescription>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {/* Add PASSED/FAILED badge for items with status */}
                              {status && (
                                <div className="flex items-center gap-1">
                                  {status === "Passed" ? (
                                    <CheckCircle
                                      size={16}
                                      style={{ color: "#0D7717" }}
                                      weight="fill"
                                    />
                                  ) : (
                                    <XCircle
                                      size={16}
                                      style={{ color: "#C4314B" }}
                                      weight="fill"
                                    />
                                  )}
                                  <span
                                    style={{
                                      fontSize: "12px",
                                      fontWeight: 600,
                                      color:
                                        status === "Passed"
                                          ? "#0D7717"
                                          : "#C4314B",
                                    }}
                                  >
                                    {status === "Passed" ? "PASSED" : "FAILED"}
                                  </span>
                                </div>
                              )}
                              <ArrowMinimize20Regular
                                className="text-muted-foreground"
                                style={{ fontSize: "14px" }}
                              />
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>{renderCardContent(item)}</CardContent>
                      </>
                    )}
                  </Card>
                );
              })}
            </div>
            {filteredCardData.length === 0 && (
              <NoDataCard
                icon={
                  <Document20Regular
                    className="text-muted-foreground mb-4"
                    style={{ fontSize: "48px" }}
                  />
                }
                title="No items found"
                description="Try selecting a different filter"
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
