import { useState } from "react";
import clsx from "clsx";
import { IconSize } from "@gouvfr-lasuite/ui-components";
import { Item } from "@/features/drivers/types";
import { ItemIcon } from "./ItemIcon";

type ItemThumbnailProps = {
  item: Item;
  // BEM block of the container, which gets a `--thumbnail` modifier when an
  // image is displayed instead of the icon.
  className: string;
};

/**
 * Displays the rendered thumbnail of an item, or the preview of an image,
 * falling back to its large icon when there is none or it fails to load.
 */
export const ItemThumbnail = ({ item, className }: ItemThumbnailProps) => {
  const [hasError, setHasError] = useState(false);
  const src =
    item.url_thumbnail ??
    (item.mimetype?.startsWith("image/") ? item.url_preview : undefined);

  if (!src || hasError) {
    return (
      <div className={className}>
        <ItemIcon item={item} size={IconSize.X_LARGE} />
      </div>
    );
  }

  return (
    <div className={clsx(className, `${className}--thumbnail`)}>
      <img
        src={src}
        alt={item.title}
        loading="lazy"
        onError={() => setHasError(true)}
      />
    </div>
  );
};
