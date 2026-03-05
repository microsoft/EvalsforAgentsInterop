import { ReactElement, JSXElementConstructor } from "react";
import {
  makeStyles,
  tokens,
  Table,
  TableHeader,
  TableHeaderCell,
  TableBody,
  TableRow,
  TableCell,
  TableCellLayout,
} from "@fluentui/react-components";
import { useSelectableClick } from "@/hooks/useSelectableClick";

const useStyles = makeStyles({
  table: {
    backgroundColor: tokens.colorNeutralBackground1,
    width: "100%",
    tableLayout: "fixed", // Ensures consistent column widths
  },
  tableRow: {
    marginLeft: "8px",
    marginRight: "8px",
  },
  tableHeaderCell: {
    paddingTop: "16px",
    paddingBottom: "16px",
    paddingLeft: "8px",
    paddingRight: "8px",
    whiteSpace: "nowrap", // Prevent header text wrapping
    overflow: "visible", // Allow focus outlines to be visible
    textOverflow: "ellipsis",
    maxWidth: 0, // This forces the ellipsis to work with flexbox
  },
  tableCell: {
    paddingTop: "16px",
    paddingBottom: "16px",
    paddingLeft: "8px",
    paddingRight: "8px",
    whiteSpace: "nowrap", // Prevent cell content wrapping
    overflow: "visible", // Allow focus outlines to be visible
    textOverflow: "ellipsis",
    maxWidth: 0, // This forces the ellipsis to work with flexbox
  },
  tableCellContent: {
    overflow: "visible", // Allow focus outlines and interactive elements to be fully visible
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    width: "100%",
  },
  tableContainer: {
    width: "100%",
    overflowX: "auto", // Enable horizontal scrolling when needed
  },
});

export interface TableColumn<T = any> {
  key: string;
  header: string;
  width?: string;
  minWidth?: string; // Minimum width to prevent columns from disappearing
  maxWidth?: string;
  render: (
    item: T
  ) => string | number | ReactElement<any, string | JSXElementConstructor<any>>;
}

export interface DataTableProps<T = any> {
  columns: TableColumn<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  emptyState?: ReactElement<any, string | JSXElementConstructor<any>>;
  minColumnWidth?: string; // Default minimum column width
}

export function DataTable<T = any>({
  columns,
  data,
  onRowClick,
  emptyState,
  minColumnWidth = "150px",
}: DataTableProps<T>) {
  const styles = useStyles();
  const { createClickHandler } = useSelectableClick();

  const handleRowClick = onRowClick
    ? createClickHandler((item: T) => onRowClick(item))
    : undefined;

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  // Calculate column styles with proper minimum widths
  const getColumnStyle = (column: TableColumn<T>) => {
    return {
      width: column.width || "auto",
      minWidth: column.minWidth || minColumnWidth,
      maxWidth: column.maxWidth || "none",
    };
  };

  return (
    <div className={styles.tableContainer}>
      <Table className={styles.table}>
        <TableHeader>
          <TableRow className={styles.tableRow}>
            {columns.map((column) => (
              <TableHeaderCell
                key={column.key}
                className={styles.tableHeaderCell}
                style={getColumnStyle(column)}
              >
                <div className={styles.tableCellContent}>{column.header}</div>
              </TableHeaderCell>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((item, index) => (
            <TableRow
              key={(item as any).id || index}
              className={styles.tableRow}
              onClick={
                handleRowClick
                  ? (event) => handleRowClick(item, event)
                  : undefined
              }
              style={{
                cursor: onRowClick ? "pointer" : "default",
                userSelect: "text",
              }}
            >
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  className={styles.tableCell}
                  style={getColumnStyle(column)}
                >
                  <div className={styles.tableCellContent}>
                    {column.render(item)}
                  </div>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
