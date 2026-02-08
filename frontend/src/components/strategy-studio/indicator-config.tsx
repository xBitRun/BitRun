"use client";

import { Activity, TrendingUp, BarChart3, Gauge } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { IndicatorSettings } from "@/types";
import { useTranslations } from "next-intl";

interface IndicatorConfigProps {
  value: IndicatorSettings;
  onChange: (settings: IndicatorSettings) => void;
}

export function IndicatorConfig({ value, onChange }: IndicatorConfigProps) {
  const t = useTranslations("strategyStudio");

  const updateEMA = (updates: Partial<IndicatorSettings["ema"]>) => {
    onChange({ ...value, ema: { ...value.ema, ...updates } });
  };

  const updateRSI = (updates: Partial<IndicatorSettings["rsi"]>) => {
    onChange({ ...value, rsi: { ...value.rsi, ...updates } });
  };

  const updateMACD = (updates: Partial<IndicatorSettings["macd"]>) => {
    onChange({ ...value, macd: { ...value.macd, ...updates } });
  };

  const updateATR = (updates: Partial<IndicatorSettings["atr"]>) => {
    onChange({ ...value, atr: { ...value.atr, ...updates } });
  };

  const handleEMAPeriodChange = (index: number, newValue: number) => {
    const periods = [...value.ema.periods];
    periods[index] = newValue;
    updateEMA({ periods: periods.sort((a, b) => a - b) });
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5 text-primary" />
          {t("indicators.title")}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {t("indicators.description")}
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* EMA Indicator */}
        <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-500" />
              <Label className="text-sm font-medium">
                {t("indicators.ema.title")}
              </Label>
              <Badge variant="outline" className="text-xs">
                EMA
              </Badge>
            </div>
            <Switch
              checked={value.ema.enabled}
              onCheckedChange={(enabled) => updateEMA({ enabled })}
            />
          </div>
          {value.ema.enabled && (
            <div className="space-y-3 pl-6">
              <p className="text-xs text-muted-foreground">
                {t("indicators.ema.description")}
              </p>
              <div className="grid grid-cols-3 gap-4">
                {value.ema.periods.map((period, index) => (
                  <div key={index} className="space-y-1">
                    <Label className="text-xs text-muted-foreground">
                      {t("indicators.ema.period")} {index + 1}
                    </Label>
                    <Input
                      type="number"
                      value={period}
                      onChange={(e) =>
                        handleEMAPeriodChange(index, parseInt(e.target.value) || 9)
                      }
                      min={1}
                      max={200}
                      className="h-8"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RSI Indicator */}
        <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-purple-500" />
              <Label className="text-sm font-medium">
                {t("indicators.rsi.title")}
              </Label>
              <Badge variant="outline" className="text-xs">
                RSI
              </Badge>
            </div>
            <Switch
              checked={value.rsi.enabled}
              onCheckedChange={(enabled) => updateRSI({ enabled })}
            />
          </div>
          {value.rsi.enabled && (
            <div className="space-y-3 pl-6">
              <p className="text-xs text-muted-foreground">
                {t("indicators.rsi.description")}
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-muted-foreground">
                    {t("indicators.rsi.period")}: {value.rsi.period}
                  </Label>
                </div>
                <Slider
                  value={[value.rsi.period]}
                  onValueChange={([period]) => updateRSI({ period })}
                  min={5}
                  max={50}
                  step={1}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>

        {/* MACD Indicator */}
        <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-green-500" />
              <Label className="text-sm font-medium">
                {t("indicators.macd.title")}
              </Label>
              <Badge variant="outline" className="text-xs">
                MACD
              </Badge>
            </div>
            <Switch
              checked={value.macd.enabled}
              onCheckedChange={(enabled) => updateMACD({ enabled })}
            />
          </div>
          {value.macd.enabled && (
            <div className="space-y-3 pl-6">
              <p className="text-xs text-muted-foreground">
                {t("indicators.macd.description")}
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t("indicators.macd.fast")}
                  </Label>
                  <Input
                    type="number"
                    value={value.macd.fast}
                    onChange={(e) =>
                      updateMACD({ fast: parseInt(e.target.value) || 12 })
                    }
                    min={1}
                    max={50}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t("indicators.macd.slow")}
                  </Label>
                  <Input
                    type="number"
                    value={value.macd.slow}
                    onChange={(e) =>
                      updateMACD({ slow: parseInt(e.target.value) || 26 })
                    }
                    min={1}
                    max={100}
                    className="h-8"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    {t("indicators.macd.signal")}
                  </Label>
                  <Input
                    type="number"
                    value={value.macd.signal}
                    onChange={(e) =>
                      updateMACD({ signal: parseInt(e.target.value) || 9 })
                    }
                    min={1}
                    max={50}
                    className="h-8"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ATR Indicator */}
        <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-orange-500" />
              <Label className="text-sm font-medium">
                {t("indicators.atr.title")}
              </Label>
              <Badge variant="outline" className="text-xs">
                ATR
              </Badge>
            </div>
            <Switch
              checked={value.atr.enabled}
              onCheckedChange={(enabled) => updateATR({ enabled })}
            />
          </div>
          {value.atr.enabled && (
            <div className="space-y-3 pl-6">
              <p className="text-xs text-muted-foreground">
                {t("indicators.atr.description")}
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-muted-foreground">
                    {t("indicators.atr.period")}: {value.atr.period}
                  </Label>
                </div>
                <Slider
                  value={[value.atr.period]}
                  onValueChange={([period]) => updateATR({ period })}
                  min={5}
                  max={50}
                  step={1}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
