import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  NavDrawer,
  NavDrawerBody,
  NavDrawerHeader,
  NavItem,
  Button,
  Tooltip,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import { PanelLeftText20Regular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  root: {
    overflow: "hidden",
    display: "flex",
    height: "100vh",
  },
  nav: {
    width: "20vw",
    minWidth: "240px",
    maxWidth: "400px",
    height: "100vh",
    borderRight: `1px solid ${tokens.colorNeutralStroke2}`,
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
  },
  navBody: {
    flex: "1",
    overflow: "auto",
    paddingLeft: "24px",
    paddingRight: "12px",
  },
  navHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    paddingRight: "8px",
    paddingLeft: "3px",
    paddingTop: "16px",
    paddingBottom: "16px",
    gap: "8px",
    flexWrap: "wrap",
  },
  titleContainer: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    flex: "1 1 auto",
    minWidth: "200px",
  },
  navItem: {
    paddingLeft: "4px", //Spacing/xs
  },
  title: {
    fontSize: tokens.fontSizeBase300,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground1,
    margin: 0,
    wordBreak: "break-word",
  },
  externalToggleButton: {
    position: "fixed",
    top: "16px",
    left: "16px",
    marginRight: "14px",
    zIndex: 1000,
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    borderRadius: tokens.borderRadiusMedium,
  },
});

export function Navigation() {
  const styles = useStyles();
  const location = useLocation();
  const navigate = useNavigate();
  const [selectedValue, setSelectedValue] = useState(location.pathname);
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    setSelectedValue(location.pathname);
  }, [location.pathname]);

  const handleSelectionChange = (path: string) => {
    setSelectedValue(path);
    navigate(path);
  };

  return (
    <>
      {!isOpen && (
        <Tooltip content="Open Navigation" relationship="label">
          <Button
            icon={<PanelLeftText20Regular />}
            appearance="subtle"
            onClick={() => setIsOpen(!isOpen)}
            className={styles.externalToggleButton}
            aria-label="Open Navigation"
          />
        </Tooltip>
      )}
      <NavDrawer
        selectedValue={selectedValue}
        open={isOpen}
        type="inline"
        className={styles.nav}
        style={{ height: "100vh", display: "flex", flexDirection: "column" }}
        {...(!isOpen ? { inert: "" } : {})}
      >
        <NavDrawerHeader>
          <div className={styles.navHeader}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <img
                src="/images/microsoftlogo.svg"
                alt="Microsoft logo"
                style={{ width: "24px", height: "24px" }}
              />
              <h1 className={styles.title}>Evals for Agent Interop</h1>
            </div>
            <Tooltip content="Close Navigation" relationship="label">
              <Button
                icon={<PanelLeftText20Regular />}
                appearance="subtle"
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Close Navigation"
              />
            </Tooltip>
          </div>
        </NavDrawerHeader>

        <NavDrawerBody className={styles.navBody}>
          <NavItem
            value="/agents"
            onClick={() => handleSelectionChange("/agents")}
            className={styles.navItem}
          >
            Agents
          </NavItem>

          <NavItem
            value="/datasets"
            onClick={() => handleSelectionChange("/datasets")}
            className={styles.navItem}
          >
            Evaluation datasets
          </NavItem>

          <NavItem
            value="/leaderboard"
            onClick={() => handleSelectionChange("/leaderboard")}
            className={styles.navItem}
          >
            Leaderboard
          </NavItem>
        </NavDrawerBody>
      </NavDrawer>
    </>
  );
}
