import { memo } from "react";
import { flexRender } from "@tanstack/react-table";
import clsx from "clsx";
import { ItemType, TRANSIENT_UPLOAD_STATES } from "@/features/drivers/types";
import { Draggable } from "@/features/explorer/components/Draggable";
import { Droppable } from "@/features/explorer/components/Droppable";
import { ItemThumbnail } from "@/features/explorer/components/icons/ItemThumbnail";
import { useIsItemSelected } from "@/features/explorer/stores/selectionStore";
import { timeAgo } from "@/features/explorer/utils/utils";
import { EmbeddedExplorerGridRowProps } from "./EmbeddedExplorerGridRow";
import { useDisableDragGridItem } from "./hooks";

/**
 * Grid view counterpart of EmbeddedExplorerGridRow: it shares the same
 * handlers and renders the name and actions cells of the row in its header.
 */
const EmbeddedExplorerGridCardComponent = ({
  row,
  isOvered,
  onClickRow,
  onContextMenuRow,
  onOver,
}: EmbeddedExplorerGridRowProps) => {
  const item = row.original;
  const isSelected = useIsItemSelected(item.id);
  const disableDrag = useDisableDragGridItem(item);
  const isTransient = TRANSIENT_UPLOAD_STATES.includes(item.upload_state);

  const renderCell = (columnId: string) => {
    const cell = row
      .getVisibleCells()
      .find((visibleCell) => visibleCell.column.id === columnId);
    return cell && flexRender(cell.column.columnDef.cell, cell.getContext());
  };

  return (
    <Droppable
      id={`${row.id}_card`}
      item={item}
      disabled={
        isSelected ||
        item.type !== ItemType.FOLDER ||
        !item.abilities?.children_create
      }
      onOver={(isOver, draggedItem) => onOver(item.id, isOver, draggedItem)}
    >
      <div
        className={clsx("explorer__grid__card", {
          selectable: !isTransient,
          selected: isSelected,
          over: isOvered,
          duplicating: isTransient,
        })}
        data-id={item.id}
        tabIndex={0}
        onClick={(e) => onClickRow(e, row)}
        onContextMenu={(e) => onContextMenuRow(e, row)}
      >
        <div className="explorer__grid__card__header">
          {renderCell("title")}
          {renderCell("actions")}
        </div>
        <Draggable
          id={`${row.id}_card`}
          item={item}
          disabled={isTransient || disableDrag}
        >
          <ItemThumbnail
            item={item}
            className="explorer__grid__card__preview"
          />
          <div className="explorer__grid__card__footer">
            {timeAgo(new Date(item.updated_at))}
          </div>
        </Draggable>
      </div>
    </Droppable>
  );
};

export const EmbeddedExplorerGridCard = memo(EmbeddedExplorerGridCardComponent);
