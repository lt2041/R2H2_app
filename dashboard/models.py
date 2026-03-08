from django.db import models



#### ---------------------- BATTERY MODEL ---------------------- ####

# DB TABLE DEFINITION FOR BATTERY MODEL
class Battery(models.Model):
    name = models.CharField(max_length=100, default='Battery')

    # degradation:
    rKt_lc = models.FloatField(default=4.14e-10)
    rKs = models.FloatField(default=1.04)
    rKT_uc = models.FloatField(default=6.93e-2)
    rAlphaSei = models.FloatField(default=5.75e-2)
    rKd1 = models.FloatField(default=1.4e5)
    rKd2 = models.FloatField(default=-5.01e-1)
    rKd3 = models.FloatField(default=-1.23e5)
    rBetaSei = models.FloatField(default=121.0)
    rTcRef = models.FloatField(default=55.0)
    rSoCRef = models.FloatField(default=0.5)

    # operational:
    arInitialSoC = models.FloatField(default=0.5)
    rFt = models.FloatField(default=0.0)
    rFc = models.FloatField(default=0.0)
    rBatteryMWh = models.FloatField(default=15)
    rInitialBatteryRating = models.FloatField(default=0.0)
    rBatteryRating = models.FloatField(default=0.0)
    rRCD = models.FloatField(default=1.0)
    rControlMinSoC = models.FloatField(default=0.5)
    rBatteryProportionalGain = models.FloatField(default=0.0)

    # replacements:
    iNumReplacements = models.PositiveIntegerField(default=0)
    aiReplacementHour = models.JSONField(default=list)

    # runtime:
    rSocAv = models.FloatField(default=0.0)
    rSocMax = models.FloatField(default=0.0)
    rSocMin = models.FloatField(default=0.0)
    rDodAv = models.FloatField(default=0.0)
    arBatteryPower = models.JSONField(default=list)
    arSoC = models.JSONField(default=list)
    arDoD = models.JSONField(default=list)

    # control:
    arBatteryDemand = models.JSONField(default=list)


    def __str__(self):
        return f"ID: {self.id}, Name: {self.name} (MWh: {self.rBatteryMWh})"
    



#### -------------------- ELECTROCELL MODEL -------------------- ####

# DEFAULTS FOR JSON FIELDS (must be functions to avoid mutable default argument issues)
def default_faraday_temp():
    return [40.0, 60.0, 80.0]

def default_faraday_f1():
    return [150.0, 200.0, 250.0]

def default_faraday_f2():
    return [0.99, 0.985, 0.98]

# DB TABLE DEFINITION FOR ELECTROCELL MODEL
class ElectroCellPEM(models.Model):
    name = models.CharField(max_length=100, default='ElectroCellPEM')

    # universal constants
    rR = models.FloatField(default=8.314)
    rF = models.FloatField(default=96485.0)

    # outputs populated by build_curves()
    arCurrentDensity = models.JSONField(default=list)
    arE_min = models.JSONField(default=list)
    arR_cell = models.JSONField(default=list)
    arV_cell = models.JSONField(default=list)

    # geometry & grid
    iNumCurrent = models.FloatField(default=1000)
    rA_cell = models.FloatField(default=1000.0, help_text="cm^2")
    rI_rated = models.FloatField(default=3.0, help_text="A/cm^2")

    # temperature references
    rT_0 = models.FloatField(default=55.0, help_text="Nominal operating temperature [°C]")
    rT = models.FloatField(default=55.0, help_text="Initial operating temperature [°C]")

    # PEM voltage model params
    rE_min0 = models.FloatField(default=1.55)
    rR_0 = models.FloatField(default=0.178, help_text="should be x2 according to literature but polarization curve would be too steep")
    rD_rt = models.FloatField(default=-0.0045 , help_text="dR/dT")

    # stack/cell nominals (informative)
    rV_cellNom = models.FloatField(default=2.1)
    rV_bank = models.FloatField(default=633.5)
    rI_bank = models.FloatField(default=3000.0)

    # Faraday eff params
    rF1 = models.FloatField(default=0.25)
    rF2 = models.FloatField(default=0.996)
    arFaradayTemp_C = models.JSONField(default=default_faraday_temp)
    arFaradayF1 = models.JSONField(default=default_faraday_f1)
    arFaradayF2 = models.JSONField(default=default_faraday_f2)
    
    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}"
