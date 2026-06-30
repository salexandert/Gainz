class AutoLinkService:
    MIN_UNLINKED_QUANTITY = 0.000001

    DESCRIPTIONS = {
        "fifo": "Added FIFO basis links for review",
        "filo": "Added FILO basis links for review",
        "min_gain_long": "Added Min Gain Long basis links for review",
        "min_gain": "Added Min Gain basis links for review",
    }

    def _normalize_asset(self, asset):
        if asset in (None, ""):
            return None

        return str(asset).strip().upper()

    def _link_matches_scope(self, link, asset=None, year=None):
        asset = self._normalize_asset(asset)

        if not getattr(link, "sell", None) or not getattr(link, "buy", None):
            return False

        if asset and str(getattr(link, "symbol", "")).upper() != asset:
            return False

        if year is not None:
            sell_time = getattr(link.sell, "time_stamp", None)
            if getattr(sell_time, "year", None) != year:
                return False

        return True

    def clear_basis_links(self, transactions, asset=None, year=None):
        removed_links = set()

        for transaction in getattr(transactions, "transactions", []) or []:
            kept_links = []
            for link in getattr(transaction, "links", []) or []:
                if self._link_matches_scope(link, asset=asset, year=year):
                    removed_links.add(link)
                else:
                    kept_links.append(link)
            transaction.links = kept_links

        for transaction in getattr(transactions, "transactions", []) or []:
            transaction.update_linked_transactions()
            transaction.set_multi_link()

        return len(removed_links)

    def auto_link(self, transactions, asset=None, algo="fifo", year=None, rebuild=False):
        if algo not in self.DESCRIPTIONS:
            raise ValueError(f"Unsupported auto-link algorithm: {algo}")

        year = self.selected_year(year)
        removed_links = self.clear_basis_links(
            transactions,
            asset=asset,
            year=year,
        ) if rebuild else 0
        links_before = len(transactions.links)
        failures = transactions.auto_link(asset=asset, algo=algo, year=year)
        links_created = len(transactions.links) - links_before

        if links_created or removed_links:
            transactions.save(description=self.DESCRIPTIONS[algo])

        if rebuild:
            return (
                f"Rebuilt basis links using {algo}. "
                f"Removed {removed_links} existing link(s), added {links_created} link(s), "
                "and kept any remaining missing basis for review."
            )

        return f"Auto Link using {algo} completed. Review generated links before using reports."

    def selected_year(self, year_value):
        if year_value is None:
            return None

        normalized = str(year_value).strip()
        if normalized in ("", "All Time"):
            return None

        return int(normalized)

    def assets_with_unlinked_sales(self, transactions, year=None, min_unlinked=None):
        min_unlinked = min_unlinked or self.MIN_UNLINKED_QUANTITY
        assets = set()

        for trans in transactions:
            if trans.trans_type != "sell":
                continue

            if trans.unlinked_quantity <= min_unlinked:
                continue

            if year is not None and trans.time_stamp.year != year:
                continue

            assets.add(trans.symbol)

        return sorted(assets)

    def auto_link_unlinked_sales(
        self,
        transactions,
        algo="fifo",
        year=None,
        save_description=None,
        rebuild=False,
    ):
        if algo not in self.DESCRIPTIONS:
            raise ValueError(f"Unsupported auto-link algorithm: {algo}")

        year = self.selected_year(year)
        removed_links = self.clear_basis_links(
            transactions,
            year=year,
        ) if rebuild else 0
        assets_needing_links = self.assets_with_unlinked_sales(transactions, year=year)
        before_link_count = len(transactions.links)
        failures = []

        for asset in assets_needing_links:
            failures.extend(transactions.auto_link(asset=asset, algo=algo, year=year))

        links_created = len(transactions.links) - before_link_count

        if links_created > 0 or removed_links > 0:
            transactions.save(
                description=save_description or f"{self.DESCRIPTIONS[algo]} across all assets"
            )

        if links_created > 0 and removed_links > 0:
            method_label = algo.replace("_", " ").upper()
            message = (
                f"Rebuilt {method_label} basis links for review. Removed "
                f"{removed_links} existing link(s) and added {links_created} "
                f"link(s) across {len(assets_needing_links)} asset(s)."
            )
        elif links_created > 0:
            method_label = algo.replace("_", " ").upper()
            message = (
                f"Added {links_created} {method_label} basis link(s) across "
                f"{len(assets_needing_links)} asset(s) for review."
            )
        elif removed_links > 0:
            message = (
                f"Removed {removed_links} existing basis link(s), but no new "
                f"{algo.replace('_', ' ').upper()} links could be created. Review missing basis."
            )
        elif assets_needing_links:
            message = (
                "No new FIFO links could be created. Review basis lots, missing acquisitions, "
                "or unsupported activity for the listed assets."
            )
        else:
            message = "No assets currently have unlinked sales available for FIFO Auto Link."

        return {
            "message": message,
            "links_created": links_created,
            "links_removed": removed_links,
            "fixed_assets": assets_needing_links,
            "failures": failures,
            "algo": algo,
            "year": year,
        }

    def ensure_default_fifo_links(self, transactions, reason="data update", year=None):
        return self.auto_link_unlinked_sales(
            transactions,
            algo="fifo",
            year=year,
            save_description=f"Automatically added FIFO basis links after {reason}",
        )


def public_auto_link_result(result):
    if not result:
        return None

    return {
        "message": result.get("message"),
        "links_created": result.get("links_created", 0),
        "links_removed": result.get("links_removed", 0),
        "fixed_assets": result.get("fixed_assets", []),
        "algo": result.get("algo"),
        "year": result.get("year"),
        "failures": [
            {
                "asset": failure.get("asset"),
                "unlinkable": failure.get("unlinkable"),
                "quantity": failure.get("quantity"),
                "timestamp": str(failure.get("timestamp")),
                "algo": failure.get("algo"),
            }
            for failure in result.get("failures", [])
        ],
    }
