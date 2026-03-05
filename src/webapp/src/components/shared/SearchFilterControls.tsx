import { ReactElement, JSXElementConstructor } from "react";
import {
  makeStyles,
  tokens,
  SearchBox,
  Dropdown,
  Option,
  Button as FluentButton,
} from "@fluentui/react-components";
import {
  ArrowSort20Regular,
  ArrowUp20Regular,
  ArrowDown20Regular,
} from "@fluentui/react-icons";

const useStyles = makeStyles({
  searchContainer: {
    marginTop: "48px",
    marginBottom: "32px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  leftControls: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalM,
  },
  searchBox: {
    width: "400px",
    minWidth: "320px",
    minHeight: "40px",
    backgroundColor: tokens.colorNeutralBackground1,
    border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    "& input": {
      borderRadius: tokens.borderRadiusXLarge,
    },
  },
  filterDropdown: {
    minWidth: "180px",
    maxWidth: "250px", // Add max width to prevent expansion
    minHeight: "40px",
    backgroundColor: tokens.colorNeutralBackground1,
    border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusXLarge,
    "& > div": {
      borderRadius: tokens.borderRadiusXLarge,
      border: "none",
      backgroundColor: "transparent",
    },
    "& input": {
      borderRadius: tokens.borderRadiusXLarge,
      border: "none",
      textDecoration: "none",
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
    },
    "& button": {
      border: "none",
      textDecoration: "none",
      borderRadius: tokens.borderRadiusXLarge,
    },
  },
  sortButton: {
    minWidth: "auto",
    minHeight: "40px",
    padding: `${tokens.spacingVerticalSNudge} ${tokens.spacingHorizontalL}`,
    borderRadius: tokens.borderRadiusXLarge,
    border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke1}`,
    backgroundColor: tokens.colorNeutralBackground1,
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
});

export type SortOrder = "none" | "asc" | "desc";

export interface FilterOption {
  key: string;
  placeholder: string;
  options: string[];
  selectedOptions: string[];
  onSelectionChange: (selectedOptions: string[]) => void;
  multiselect?: boolean;
  minWidth?: string;
}

export interface SearchFilterControlsProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  filters?: FilterOption[];
  sortOrder: SortOrder;
  onSortChange: () => void;
  sortLabel?: string;
  additionalControls?: ReactElement<any, string | JSXElementConstructor<any>>;
}

export function SearchFilterControls({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search",
  filters = [],
  sortOrder,
  onSortChange,
  sortLabel = "Sort",
  additionalControls,
}: SearchFilterControlsProps) {
  const styles = useStyles();

  // Helper function to create truncated display text for multiselect
  const getDisplayValue = (filter: FilterOption) => {
    if (!filter.multiselect || filter.selectedOptions.length === 0) {
      return filter.selectedOptions.join(", ");
    }

    const maxLength = 30; // Maximum characters to show
    const selectedText = filter.selectedOptions.join(", ");

    if (selectedText.length <= maxLength) {
      return selectedText;
    }

    // Show first item and count
    const firstItem = filter.selectedOptions[0];
    const remainingCount = filter.selectedOptions.length - 1;

    if (remainingCount === 1) {
      return `${firstItem}, +1 more`;
    } else {
      return `${firstItem}, +${remainingCount} more`;
    }
  };

  const getSortIcon = () => {
    switch (sortOrder) {
      case "asc":
        return <ArrowUp20Regular />;
      case "desc":
        return <ArrowDown20Regular />;
      default:
        return <ArrowSort20Regular />;
    }
  };

  const getSortTitle = () => {
    switch (sortOrder) {
      case "asc":
        return "Sorted A-Z";
      case "desc":
        return "Sorted Z-A";
      default:
        return `Sort by ${sortLabel.toLowerCase()}`;
    }
  };

  return (
    <div className={styles.searchContainer}>
      <div className={styles.leftControls}>
        <SearchBox
          appearance="outline"
          className={styles.searchBox}
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={(_, data) => onSearchChange(data.value)}
        />
        {filters.map((filter) => (
          <Dropdown
            key={filter.key}
            className={styles.filterDropdown}
            style={{ minWidth: filter.minWidth || "180px", maxWidth: "250px" }}
            placeholder={filter.placeholder}
            aria-label={filter.placeholder}
            multiselect={filter.multiselect}
            value={getDisplayValue(filter)}
            selectedOptions={filter.selectedOptions}
            onOptionSelect={(_, data) => {
              if (data.selectedOptions) {
                filter.onSelectionChange(data.selectedOptions);
              }
            }}
          >
            {filter.options.map((option) => (
              <Option key={option} value={option}>
                {option}
              </Option>
            ))}
          </Dropdown>
        ))}
        {additionalControls}
      </div>
      <FluentButton
        className={styles.sortButton}
        appearance="outline"
        icon={getSortIcon()}
        onClick={onSortChange}
        title={getSortTitle()}
      >
        {sortLabel}
      </FluentButton>
    </div>
  );
}
