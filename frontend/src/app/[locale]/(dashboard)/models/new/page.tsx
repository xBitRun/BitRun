"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import {
  Eye,
  EyeOff,
  AlertCircle,
  Cpu,
  Settings,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Globe,
  ShieldCheck,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { FormPageHeader, CollapsibleCard } from "@/components/layout";
import { usePresetProviders, useApiFormats, getProviderIcon } from "@/hooks";
import { providersApi } from "@/lib/api";

export default function NewProviderPage() {
  const t = useTranslations("models");
  const router = useRouter();
  const toast = useToast();
  const { mutate } = useSWRConfig();

  const { presets } = usePresetProviders();
  const { formats } = useApiFormats();

  const [showApiKey, setShowApiKey] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showTips, setShowTips] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [selectedPreset, setSelectedPreset] = useState<string>("custom");
  const [formData, setFormData] = useState({
    name: "",
    note: "",
    website_url: "",
    api_key: "",
    base_url: "",
    api_format: "openai",
  });

  // Update form when preset changes
  const handlePresetChange = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = presets.find((p) => p.id === presetId);
    if (preset) {
      setFormData((prev) => ({
        ...prev,
        name: preset.name,
        base_url: preset.base_url,
        api_format: preset.api_format,
        website_url: preset.website_url,
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        name: "",
        base_url: "",
        api_format: "openai",
        website_url: "",
      }));
    }
  };

  const handleCreateProvider = async () => {
    if (!formData.name.trim() || !formData.api_key.trim()) {
      setSubmitError(t("dialog.requiredFields"));
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await providersApi.create({
        provider_type: selectedPreset,
        name: formData.name,
        note: formData.note || undefined,
        website_url: formData.website_url || undefined,
        api_key: formData.api_key,
        base_url: formData.base_url || undefined,
        api_format: formData.api_format,
      });
      toast.success(t("dialog.success"));
      await mutate("provider-configs");
      router.push("/models");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to add provider";
      setSubmitError(message);
      toast.error(t("dialog.error"), message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = Boolean(formData.name.trim() && formData.api_key.trim());
  const selectedPresetInfo = presets.find((p) => p.id === selectedPreset);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header - Using shared FormPageHeader component */}
      <FormPageHeader
        backHref="/models"
        title={t("dialog.title")}
        subtitle={t("dialog.description")}
        icon={<Cpu className="w-6 h-6 text-primary" />}
        cancelLabel={t("dialog.cancel")}
        submitLabel={t("dialog.add")}
        onSubmit={handleCreateProvider}
        isSubmitting={isSubmitting}
        isValid={isFormValid}
      />

      {/* Error Alert */}
      {submitError && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{submitError}</p>
        </div>
      )}

      {/* Provider Selection - Compact Row */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <Label className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-primary" />
              {t("dialog.selectProvider")}
            </Label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handlePresetChange("custom")}
                className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedPreset === "custom"
                    ? "border-primary/50 bg-primary/10 text-foreground"
                    : "border-border/50 hover:border-border text-muted-foreground"
                }`}
              >
                <Settings className="w-4 h-4" />
                {t("dialog.customConfig")}
              </button>
              {presets
                .filter((p) => p.id !== "custom")
                .map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handlePresetChange(preset.id)}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all flex items-center gap-2 ${
                      selectedPreset === preset.id
                        ? "border-primary/50 bg-primary/10 text-foreground"
                        : "border-border/50 hover:border-border text-muted-foreground"
                    }`}
                  >
                    <span>{getProviderIcon(preset.id)}</span>
                    {preset.name}
                  </button>
                ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {t("dialog.presetHint")}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Provider Configuration - Core Section */}
      <Card className="border-primary/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-primary" />
                {t("newPage.configuration")}
              </CardTitle>
              <CardDescription className="mt-1">
                {t("newPage.configurationDesc")}
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowTips(!showTips)}
              className="text-muted-foreground"
            >
              <Lightbulb className="w-4 h-4 mr-1" />
              {t("newPage.tips")}
              {showTips ? (
                <ChevronUp className="w-4 h-4 ml-1" />
              ) : (
                <ChevronDown className="w-4 h-4 ml-1" />
              )}
            </Button>
          </div>

          {/* Collapsible Tips */}
          {showTips && (
            <div className="mt-4 p-4 rounded-lg bg-muted/50 text-sm space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="font-medium mb-1">{t("newPage.tipApiKey")}</p>
                  <p className="text-muted-foreground text-xs">
                    {t("newPage.tipApiKeyDesc")}
                  </p>
                </div>
                <div>
                  <p className="font-medium mb-1">{t("newPage.tipFormat")}</p>
                  <p className="text-muted-foreground text-xs">
                    {t("newPage.tipFormatDesc")}
                  </p>
                </div>
                <div>
                  <p className="font-medium mb-1">{t("newPage.tipTest")}</p>
                  <p className="text-muted-foreground text-xs">
                    {t("newPage.tipTestDesc")}
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Selected Provider Info Banner */}
          {selectedPresetInfo && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
              <span className="text-2xl">
                {getProviderIcon(selectedPresetInfo.id)}
              </span>
              <div>
                <p className="font-medium">{selectedPresetInfo.name}</p>
                <p className="text-xs text-muted-foreground">
                  {selectedPresetInfo.base_url || t("newPage.officialEndpoint")}
                </p>
              </div>
            </div>
          )}

          {/* Basic Info Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t("dialog.providerName")} *</Label>
              <Input
                id="name"
                placeholder={t("dialog.namePlaceholder")}
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="note">{t("dialog.note")}</Label>
              <Input
                id="note"
                placeholder={t("dialog.notePlaceholder")}
                value={formData.note}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, note: e.target.value }))
                }
              />
            </div>
          </div>

          {/* API Key - Full Width */}
          <div className="space-y-2">
            <Label htmlFor="api_key">{t("dialog.apiKey")} *</Label>
            <div className="relative">
              <Input
                id="api_key"
                type={showApiKey ? "text" : "password"}
                placeholder={t("dialog.apiKeyPlaceholder")}
                value={formData.api_key}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, api_key: e.target.value }))
                }
                className="pr-10 font-mono"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>

          {/* API Format */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="api_format">{t("dialog.apiFormat")}</Label>
              <Select
                value={formData.api_format}
                onValueChange={(value) =>
                  setFormData((prev) => ({ ...prev, api_format: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {formats.length > 0 ? (
                    formats.map((format) => (
                      <SelectItem key={format.id} value={format.id}>
                        {format.name}
                      </SelectItem>
                    ))
                  ) : (
                    <>
                      <SelectItem value="openai">
                        OpenAI Chat Completions
                      </SelectItem>
                      <SelectItem value="anthropic">
                        Anthropic Messages
                      </SelectItem>
                      <SelectItem value="gemini">Google Gemini</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {t("dialog.apiFormatHint")}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="website_url">{t("dialog.websiteUrl")}</Label>
              <Input
                id="website_url"
                placeholder="https://example.com"
                value={formData.website_url}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    website_url: e.target.value,
                  }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Settings - Collapsible */}
      <CollapsibleCard
        open={showAdvanced}
        onOpenChange={setShowAdvanced}
        title={t("newPage.advancedSettings")}
        description={t("newPage.advancedSettingsDesc")}
        icon={<Globe className="w-4 h-4 text-primary" />}
      >
        <div className="grid grid-cols-1 gap-4">
          <div className="space-y-2">
            <Label htmlFor="base_url">{t("dialog.baseUrl")}</Label>
            <Input
              id="base_url"
              placeholder="https://api.example.com/v1"
              value={formData.base_url}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, base_url: e.target.value }))
              }
              className="font-mono"
            />
            <p className="text-xs text-muted-foreground">
              {t("dialog.baseUrlHint")}
            </p>
          </div>

          {/* Security Note */}
          <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
            <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-primary">
                {t("newPage.securityTitle")}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("newPage.securityDesc")}
              </p>
            </div>
          </div>
        </div>
      </CollapsibleCard>
    </div>
  );
}
