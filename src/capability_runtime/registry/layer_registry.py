from __future__ import annotations

from ..core.errors import DuplicateLayerError, LayerNotFoundError
from ..core.layer import Layer


class LayerRegistry:
    def __init__(self) -> None:
        self._by_name: dict[str, Layer] = {}
        self._by_order: dict[int, Layer] = {}

    def register(self, layer: Layer | str, order: int | None = None) -> Layer:
        value = (
            layer
            if isinstance(layer, Layer)
            else Layer(
                order=order if order is not None else len(self._by_name),
                name=layer,
            )
        )
        if value.name in self._by_name:
            raise DuplicateLayerError(f"Layer name already registered: {value.name}")
        if value.order in self._by_order:
            raise DuplicateLayerError(f"Layer order already registered: {value.order}")
        self._by_name[value.name] = value
        self._by_order[value.order] = value
        return value

    def get(self, name: str) -> Layer:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise LayerNotFoundError(f"Layer not found: {name}") from exc

    def all(self) -> tuple[Layer, ...]:
        return tuple(sorted(self._by_name.values()))
