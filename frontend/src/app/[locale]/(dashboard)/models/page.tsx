"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  Plus,
  MoreHorizontal,
  Trash2,
  Loader2,
  Check,
  X,
  ExternalLink,
  RefreshCw,
  Cpu,
  ChevronDown,
  ChevronUp,
  Zap,
  Brain,
  DollarSign,
  AlertCircle,
} from "lucide-react";
import {
  ListPageSkeleton,
  ListPageError,
  ListPageEmpty,
} from "@/components/list-page";
import { useToast } from "@/components/ui/toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  useProviderConfigs,
  useModels,
  getProviderIcon,
  getProviderConfigDisplayName,
} from "@/hooks";
import { providersApi, modelsApi } from "@/lib/api";
import type { ProviderConfigResponse, AIModelInfoResponse } from "@/lib/api";

// Add Model Dialog Component (works for any provider)
interface AddModelDialogProps {
  providerId: string;
  onAdd: (
    providerId: string,
    data: {
      id: string;
      name: string;
      description?: string;
      context_window?: number;
      max_output_tokens?: number;
      supports_json_mode?: boolean;
    },
  ) => Promise<void>;
  t: ReturnType<typeof useTranslations>;
}

function AddModelDialog({ providerId, onAdd, t }: AddModelDialogProps) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    id: "",
    name: "",
    description: "",
    context_window: 128000,
    max_output_tokens: 4096,
    supports_json_mode: false,
  });

  const handleSubmit = async () => {
    if (!formData.id || !formData.name) return;

    setIsSubmitting(true);
    try {
      await onAdd(providerId, {
        id: formData.id,
        name: formData.name,
        description: formData.description || undefined,
        context_window: formData.context_window,
        max_output_tokens: formData.max_output_tokens,
        supports_json_mode: formData.supports_json_mode,
      });
      setOpen(false);
      setFormData({
        id: "",
        name: "",
        description: "",
        context_window: 128000,
        max_output_tokens: 4096,
        supports_json_mode: false,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full h-9 text-xs">
          <Plus className="w-3 h-3 mr-1" />
          {t("customModel.add")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("customModel.title")}</DialogTitle>
          <DialogDescription>{t("customModel.description")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="model_id">{t("customModel.modelId")} *</Label>
            <Input
              id="model_id"
              placeholder={t("customModel.modelIdPlaceholder")}
              value={formData.id}
              onChange={(e) => setFormData({ ...formData, id: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">{t("customModel.name")} *</Label>
            <Input
              id="name"
              placeholder={t("customModel.namePlaceholder")}
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">
              {t("customModel.modelDescription")}
            </Label>
            <Textarea
              id="description"
              placeholder={t("customModel.descriptionPlaceholder")}
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={2}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="context_window">
                {t("customModel.contextWindow")}
              </Label>
              <Input
                id="context_window"
                type="number"
                value={formData.context_window}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    context_window: parseInt(e.target.value) || 128000,
                  })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_output">{t("customModel.maxOutput")}</Label>
              <Input
                id="max_output"
                type="number"
                value={formData.max_output_tokens}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_output_tokens: parseInt(e.target.value) || 4096,
                  })
                }
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="json_mode"
              checked={formData.supports_json_mode}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, supports_json_mode: checked })
              }
            />
            <Label htmlFor="json_mode" className="text-sm">
              {t("customModel.supportsJsonMode")}
            </Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {t("customModel.cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !formData.id || !formData.name}
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : null}
            {t("customModel.addModel")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Model Item Component
interface ModelItemProps {
  model: AIModelInfoResponse;
  providerId: string;
  onTest: (modelId: string) => Promise<void>;
  onDelete: (providerId: string, modelId: string) => Promise<void>;
  t: ReturnType<typeof useTranslations>;
}

function ModelItem({ model, providerId, onTest, onDelete, t }: ModelItemProps) {
  const [isTesting, setIsTesting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleTest = async () => {
    setIsTesting(true);
    try {
      await onTest(model.id);
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = async () => {
    // Extract model_id from full id (provider:model_id)
    const modelApiId = model.id.includes(":")
      ? model.id.split(":", 2)[1]
      : model.id;
    setIsDeleting(true);
    try {
      await onDelete(providerId, modelApiId);
    } finally {
      setIsDeleting(false);
    }
  };

  // Format number with K/M suffix
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
    return num.toString();
  };

  return (
    <div className="p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-primary shrink-0" />
            <span className="font-medium text-sm truncate">{model.name}</span>
          </div>
          {model.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {model.description}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              {formatNumber(model.context_window)} ctx
            </span>
            <span className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />${model.cost_per_1k_input}/
              {model.cost_per_1k_output}
            </span>
            {model.supports_vision && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {t("card.vision")}
              </Badge>
            )}
            {model.supports_json_mode && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {t("card.json")}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={handleTest}
            disabled={isTesting}
          >
            {isTesting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              t("modelList.test")
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// Provider Card Component
interface ProviderCardProps {
  provider: ProviderConfigResponse;
  onDelete: (id: string) => void;
  onTest: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
  onTestModel: (modelId: string) => Promise<void>;
  onAddModel: (
    providerId: string,
    data: {
      id: string;
      name: string;
      description?: string;
      context_window?: number;
      max_output_tokens?: number;
      supports_json_mode?: boolean;
    },
  ) => Promise<void>;
  onDeleteModel: (providerId: string, modelId: string) => Promise<void>;
  t: ReturnType<typeof useTranslations>;
}

function ProviderCard({
  provider,
  onDelete,
  onTest,
  onToggle,
  onTestModel,
  onAddModel,
  onDeleteModel,
  t,
}: ProviderCardProps) {
  const [isTesting, setIsTesting] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  // Fetch models when expanded
  const {
    models,
    isLoading: modelsLoading,
    error: modelsError,
    refresh: refreshModels,
  } = useModels(isExpanded ? provider.provider_type : undefined);

  const handleAddModel = async (
    providerId: string,
    data: Parameters<typeof onAddModel>[1],
  ) => {
    await onAddModel(providerId, data);
    refreshModels();
  };

  const handleDeleteModel = async (providerId: string, modelId: string) => {
    await onDeleteModel(providerId, modelId);
    refreshModels();
  };

  const handleTest = async () => {
    setIsTesting(true);
    try {
      await onTest(provider.id);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <Card
      className={cn(
        "bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors",
        !provider.is_enabled && "opacity-60",
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {getProviderIcon(provider.provider_type)}
            </div>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                {provider.name}
                {!provider.is_enabled && (
                  <Badge variant="secondary" className="text-xs">
                    {t("card.disabled")}
                  </Badge>
                )}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {getProviderConfigDisplayName(provider.provider_type)}
              </p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleTest} disabled={isTesting}>
                {isTesting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                {t("menu.testConnection")}
              </DropdownMenuItem>
              {provider.website_url && (
                <DropdownMenuItem asChild>
                  <a
                    href={provider.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    {t("menu.openWebsite")}
                  </a>
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(provider.id)}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t("menu.delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Row */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
          <span className="text-sm text-muted-foreground">
            {t("card.apiKey")}
          </span>
          <div className="flex items-center gap-2">
            {provider.has_api_key ? (
              <>
                <Check className="w-4 h-4 text-[var(--profit)]" />
                <span className="text-sm text-[var(--profit)]">
                  {t("card.configured")}
                </span>
              </>
            ) : (
              <>
                <X className="w-4 h-4 text-[var(--loss)]" />
                <span className="text-sm text-[var(--loss)]">
                  {t("card.notConfigured")}
                </span>
              </>
            )}
          </div>
        </div>

        {/* API Format */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {t("card.apiFormat")}
          </span>
          <Badge variant="outline" className="text-xs">
            {provider.api_format.toUpperCase()}
          </Badge>
        </div>

        {/* Base URL */}
        {provider.base_url && (
          <div className="space-y-1">
            <span className="text-sm text-muted-foreground">
              {t("card.endpoint")}
            </span>
            <p className="text-xs font-mono text-foreground/80 truncate">
              {provider.base_url}
            </p>
          </div>
        )}

        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between pt-2 border-t border-border/30">
          <span className="text-sm">{t("card.enabled")}</span>
          <Switch
            checked={provider.is_enabled}
            onCheckedChange={(checked) => onToggle(provider.id, checked)}
          />
        </div>

        {/* Note */}
        {provider.note && (
          <p className="text-xs text-muted-foreground italic">
            {provider.note}
          </p>
        )}

        {/* Model List Collapsible */}
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className="w-full justify-between h-9 px-3 text-sm"
            >
              <span className="flex items-center gap-2">
                <Brain className="w-4 h-4" />
                {t("modelList.title")}
                {isExpanded && models.length > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {models.length}
                  </Badge>
                )}
              </span>
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2 space-y-2">
            {modelsLoading ? (
              <div className="space-y-2">
                {[...Array(2)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-lg" />
                ))}
              </div>
            ) : modelsError ? (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-destructive/10 border border-destructive/30">
                <AlertCircle className="w-5 h-5 shrink-0 text-destructive" />
                <p className="text-sm text-destructive flex-1">
                  {t("modelList.loadFailed")}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refreshModels()}
                >
                  {t("modelList.retry")}
                </Button>
              </div>
            ) : models.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {models.map((model) => (
                  <ModelItem
                    key={model.id}
                    model={model}
                    providerId={provider.id}
                    onTest={onTestModel}
                    onDelete={handleDeleteModel}
                    t={t}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                {t("modelList.empty")}
              </p>
            )}
            {/* Add Model Button - available for all providers */}
            <AddModelDialog
              providerId={provider.id}
              onAdd={handleAddModel}
              t={t}
            />
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}

// Main Page Component
export default function ModelsPage() {
  const t = useTranslations("models");
  const toast = useToast();

  const { providers, isLoading, error, refresh } = useProviderConfigs();

  const handleDeleteProvider = async (id: string) => {
    if (!confirm(t("confirmDelete"))) return;

    try {
      await providersApi.delete(id);
      refresh();
      toast.success(t("deleteSuccess"));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("error.failedToDeleteProvider");
      toast.error(t("deleteError"), message);
    }
  };

  const handleTestConnection = async (id: string) => {
    try {
      const result = await providersApi.test(id);
      if (result.success) {
        toast.success(t("testSuccess"), result.message);
      } else {
        toast.error(t("testFailed"), result.message);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Connection test failed";
      toast.error(t("testFailed"), message);
    }
  };

  const handleToggleProvider = async (id: string, enabled: boolean) => {
    try {
      await providersApi.update(id, { is_enabled: enabled });
      refresh();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("error.failedToUpdateProvider");
      toast.error(t("updateError"), message);
    }
  };

  const handleTestModel = async (modelId: string) => {
    try {
      const result = await modelsApi.test({ model_id: modelId });
      if (result.success) {
        toast.success(t("modelList.testSuccess"), result.message);
      } else {
        const message = result.error_code
          ? t(
              `modelList.testError.${result.error_code}` as
                | "modelList.testError.no_api_key"
                | "modelList.testError.no_base_url"
                | "modelList.testError.connection_error"
                | "modelList.testError.auth_error"
                | "modelList.testError.model_not_found"
                | "modelList.testError.rate_limit"
                | "modelList.testError.api_error"
                | "modelList.testError.unknown",
            )
          : result.message;
        toast.error(t("modelList.testFailed"), message);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Model test failed";
      toast.error(t("modelList.testFailed"), message);
    }
  };

  const handleAddModel = async (
    providerId: string,
    data: {
      id: string;
      name: string;
      description?: string;
      context_window?: number;
      max_output_tokens?: number;
      supports_json_mode?: boolean;
    },
  ) => {
    try {
      await providersApi.addModel(providerId, {
        id: data.id,
        name: data.name,
        description: data.description,
        context_window: data.context_window,
        max_output_tokens: data.max_output_tokens,
        supports_json_mode: data.supports_json_mode,
      });
      toast.success(t("customModel.success"));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("error.failedToAddModel");
      toast.error(t("customModel.error"), message);
      throw err;
    }
  };

  const handleDeleteModel = async (providerId: string, modelId: string) => {
    try {
      await providersApi.deleteModel(providerId, modelId);
      toast.success(t("modelList.deleteSuccess"));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("error.failedToDeleteModel");
      toast.error(t("modelList.deleteFailed"), message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Link href="/models/new">
          <Button className="glow-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t("addProvider")}
          </Button>
        </Link>
      </div>

      {/* Loading */}
      {isLoading && <ListPageSkeleton />}

      {/* Error */}
      {error && (
        <ListPageError
          message={error.message || t("error.loadFailed")}
          onRetry={() => refresh()}
          retryLabel={t("retry")}
        />
      )}

      {/* Empty - no providers */}
      {!isLoading && !error && providers.length === 0 && (
        <ListPageEmpty
          icon={Cpu}
          title={t("empty.title")}
          description={t("empty.description")}
          actionLabel={t("addProvider")}
          actionHref="/models/new"
          actionIcon={Plus}
        />
      )}

      {/* Provider Cards + Add card when has data */}
      {!isLoading && !error && providers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {providers.map((provider) => (
            <ProviderCard
              key={provider.id}
              provider={provider}
              onDelete={handleDeleteProvider}
              onTest={handleTestConnection}
              onToggle={handleToggleProvider}
              onTestModel={handleTestModel}
              onAddModel={handleAddModel}
              onDeleteModel={handleDeleteModel}
              t={t}
            />
          ))}

          <Link href="/models/new" className="block h-full">
            <Card className="bg-card/30 backdrop-blur-sm border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardContent className="flex flex-col items-center justify-center h-full min-h-[280px] text-muted-foreground hover:text-foreground transition-colors">
                <div className="p-4 rounded-full bg-muted/30 mb-4">
                  <Plus className="w-8 h-8" />
                </div>
                <p className="font-medium">{t("addCard.title")}</p>
                <p className="text-sm text-center mt-1">
                  {t("addCard.subtitle")}
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>
      )}
    </div>
  );
}
